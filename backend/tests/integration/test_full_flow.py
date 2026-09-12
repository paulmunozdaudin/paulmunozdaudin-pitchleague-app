from datetime import datetime, timedelta, timezone

from app.models.gameweek import Match


def _create_and_join_league(client, alice_headers, bob_headers):
    create_resp = client.post("/api/v1/leagues", json={"name": "Los Desgraciados"}, headers=alice_headers)
    assert create_resp.status_code == 201
    league = create_resp.json()
    assert league["invite_code"].startswith("PL-")
    assert league["is_admin"] is True

    join_resp = client.post(
        "/api/v1/leagues/join", json={"invite_code": league["invite_code"]}, headers=bob_headers
    )
    assert join_resp.status_code == 200
    assert join_resp.json()["id"] == league["id"]
    return league


def test_create_join_and_list_leagues(client, alice_headers, bob_headers):
    league = _create_and_join_league(client, alice_headers, bob_headers)

    detail = client.get(f"/api/v1/leagues/{league['id']}", headers=alice_headers).json()
    assert detail["member_count"] == 2
    assert {m["user"]["name"] for m in detail["members"]} == {"Alice", "Bob"}

    mine = client.get("/api/v1/leagues", headers=bob_headers).json()
    assert len(mine) == 1 and mine[0]["id"] == league["id"]


def test_only_members_can_see_league(client, alice_headers, bob_headers):
    create_resp = client.post("/api/v1/leagues", json={"name": "Solo Alice"}, headers=alice_headers)
    league = create_resp.json()

    # Bob never joined this league — he should be forbidden from viewing it.
    outsider_resp = client.get(f"/api/v1/leagues/{league['id']}", headers=bob_headers)
    assert outsider_resp.status_code == 403


def test_admin_can_rename_and_kick_but_member_cannot(client, alice_headers, bob_headers):
    league = _create_and_join_league(client, alice_headers, bob_headers)

    forbidden = client.patch(f"/api/v1/leagues/{league['id']}", json={"name": "Nuevo nombre"}, headers=bob_headers)
    assert forbidden.status_code == 403

    ok = client.patch(f"/api/v1/leagues/{league['id']}", json={"name": "Nuevo nombre"}, headers=alice_headers)
    assert ok.status_code == 200 and ok.json()["name"] == "Nuevo nombre"

    bob_id = client.get("/api/v1/auth/me", headers=bob_headers).json()["id"]
    kick = client.delete(f"/api/v1/leagues/{league['id']}/members/{bob_id}", headers=alice_headers)
    assert kick.status_code == 204

    still_forbidden = client.get(f"/api/v1/leagues/{league['id']}", headers=bob_headers)
    assert still_forbidden.status_code == 403


def _generate_gameweek(client, league_id, alice_headers):
    resp = client.post(f"/api/v1/leagues/{league_id}/gameweeks/generate-next", headers=alice_headers)
    assert resp.status_code == 201
    return resp.json()


def _winner_home_quote(match):
    return next(o for o in match["odds"] if o["market"] == "winner" and o["selection"] == "home")


def test_bet_budget_enforced_and_stake_locks_funds(client, alice_headers, bob_headers):
    league = _create_and_join_league(client, alice_headers, bob_headers)
    gameweek = _generate_gameweek(client, league["id"], alice_headers)
    match = gameweek["matches"][0]
    winner_home = _winner_home_quote(match)

    over_budget = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/bets",
        json={
            "stake": 999_999,
            "legs": [
                {
                    "match_id": match["id"],
                    "market": "winner",
                    "selection": "home",
                    "expected_price": winner_home["price"],
                }
            ],
        },
        headers=alice_headers,
    )
    assert over_budget.status_code == 400

    placed = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/bets",
        json={
            "stake": 2500,
            "legs": [
                {
                    "match_id": match["id"],
                    "market": "winner",
                    "selection": "home",
                    "expected_price": winner_home["price"],
                }
            ],
        },
        headers=alice_headers,
    )
    assert placed.status_code == 200
    body = placed.json()
    assert body["stake"] == 2500
    assert float(body["combined_odds"]) == float(winner_home["price"])
    bet_id = body["id"]

    current = client.get(f"/api/v1/leagues/{league['id']}/gameweeks/current", headers=alice_headers).json()
    assert current["my_wallet_balance"] == current["my_wallet_starting"] - 2500

    # Placing a second, separate bet debits the same shared weekly wallet.
    second = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/bets",
        json={
            "stake": 1000,
            "legs": [
                {
                    "match_id": match["id"],
                    "market": "double_chance",
                    "selection": "home_or_draw",
                    "expected_price": next(
                        o for o in match["odds"] if o["market"] == "double_chance" and o["selection"] == "home_or_draw"
                    )["price"],
                }
            ],
        },
        headers=alice_headers,
    )
    assert second.status_code == 200
    current_after = client.get(f"/api/v1/leagues/{league['id']}/gameweeks/current", headers=alice_headers).json()
    assert current_after["my_wallet_balance"] == current_after["my_wallet_starting"] - 2500 - 1000

    # Cancelling the first bet refunds only its own stake.
    cancel = client.delete(
        f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/bets/{bet_id}", headers=alice_headers
    )
    assert cancel.status_code == 204
    current_final = client.get(f"/api/v1/leagues/{league['id']}/gameweeks/current", headers=alice_headers).json()
    assert current_final["my_wallet_balance"] == current_final["my_wallet_starting"] - 1000


def test_combination_bet_rejects_duplicate_match_and_stale_odds(client, alice_headers):
    league = client.post("/api/v1/leagues", json={"name": "Liga Combos"}, headers=alice_headers).json()
    gameweek = _generate_gameweek(client, league["id"], alice_headers)
    match_a, match_b = gameweek["matches"][0], gameweek["matches"][1]
    quote_a, quote_b = _winner_home_quote(match_a), _winner_home_quote(match_b)

    duplicate = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/bets",
        json={
            "stake": 1000,
            "legs": [
                {"match_id": match_a["id"], "market": "winner", "selection": "home", "expected_price": quote_a["price"]},
                {"match_id": match_a["id"], "market": "double_chance", "selection": "home_or_draw", "expected_price": "1.10"},
            ],
        },
        headers=alice_headers,
    )
    assert duplicate.status_code == 400

    stale = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/bets",
        json={
            "stake": 1000,
            "legs": [{"match_id": match_a["id"], "market": "winner", "selection": "home", "expected_price": "999.99"}],
        },
        headers=alice_headers,
    )
    assert stale.status_code == 409
    assert "expected_price" in stale.json()["detail"]

    combo = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/bets",
        json={
            "stake": 1000,
            "legs": [
                {"match_id": match_a["id"], "market": "winner", "selection": "home", "expected_price": quote_a["price"]},
                {"match_id": match_b["id"], "market": "winner", "selection": "home", "expected_price": quote_b["price"]},
            ],
        },
        headers=alice_headers,
    )
    assert combo.status_code == 200
    body = combo.json()
    expected_combined = round(float(quote_a["price"]) * float(quote_b["price"]), 2)
    assert float(body["combined_odds"]) == expected_combined
    assert len(body["legs"]) == 2


def test_settlement_pays_out_and_updates_ranking(client, db_session, alice_headers, bob_headers):
    league = _create_and_join_league(client, alice_headers, bob_headers)
    gameweek = _generate_gameweek(client, league["id"], alice_headers)

    for match in gameweek["matches"]:
        winner_home = _winner_home_quote(match)
        for headers in (alice_headers, bob_headers):
            client.post(
                f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/bets",
                json={
                    "stake": 1000,
                    "legs": [
                        {
                            "match_id": match["id"],
                            "market": "winner",
                            "selection": "home",
                            "expected_price": winner_home["price"],
                        }
                    ],
                },
                headers=headers,
            )

    # Force every match into the past so the settlement job will fetch results.
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.query(Match).update({"kickoff_at": past})
    db_session.commit()

    settle_resp = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/settle", headers=alice_headers
    )
    assert settle_resp.status_code == 200
    assert settle_resp.json()["settled"] is True
    assert settle_resp.json()["status"] == "settled"

    ranking = client.get(f"/api/v1/leagues/{league['id']}/rankings/{gameweek['id']}", headers=alice_headers).json()
    assert len(ranking) == 2
    assert {row["position"] for row in ranking} == {1, 2}

    notifications = client.get("/api/v1/notifications", headers=alice_headers).json()
    settled_notification = next(n for n in notifications if n["type"] == "gameweek_settled")
    # The frontend deep-links straight to the results screen from this
    # notification — both ids must be present or that link silently breaks.
    assert settled_notification["data"]["league_id"] == league["id"]
    assert settled_notification["data"]["gameweek_id"] == gameweek["id"]

    stats = client.get("/api/v1/profile/me/stats", headers=alice_headers).json()
    assert stats["gameweeks_played"] == 1

    summary = client.get(
        f"/api/v1/leagues/{league['id']}/rankings/{gameweek['id']}/result-summary", headers=alice_headers
    ).json()
    assert summary["total_picks"] == len(gameweek["matches"])

    activity = client.get(f"/api/v1/leagues/{league['id']}/activity", headers=alice_headers).json()
    assert any(a["type"] == "bet_placed" for a in activity)


def test_match_insight_falls_back_to_market_when_no_model_is_trained(client, alice_headers, bob_headers):
    league = _create_and_join_league(client, alice_headers, bob_headers)
    gameweek = _generate_gameweek(client, league["id"], alice_headers)
    match = gameweek["matches"][0]

    resp = client.get(f"/api/v1/leagues/{league['id']}/matches/{match['id']}/insight", headers=alice_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "heuristic"
    # No ModelVersion exists in this fresh test database, so the engine
    # must fall back to the de-vigged market price rather than fabricate one.
    assert body["model"]["source"] == "market"
    assert body["summary"]
