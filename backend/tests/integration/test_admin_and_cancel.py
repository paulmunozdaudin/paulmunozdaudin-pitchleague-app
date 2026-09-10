def _create_and_join_league(client, alice_headers, bob_headers):
    league = client.post("/api/v1/leagues", json={"name": "Reset Test League"}, headers=alice_headers).json()
    client.post("/api/v1/leagues/join", json={"invite_code": league["invite_code"]}, headers=bob_headers)
    return league


def test_cancel_prediction_refunds_wallet(client, alice_headers, bob_headers):
    league = _create_and_join_league(client, alice_headers, bob_headers)
    gameweek = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/generate-next", headers=alice_headers
    ).json()
    match = gameweek["matches"][0]

    placed = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/predictions",
        json={"match_id": match["id"], "market": "winner", "selection": "home", "stake": 3000},
        headers=alice_headers,
    ).json()

    after_stake = client.get(f"/api/v1/leagues/{league['id']}/gameweeks/current", headers=alice_headers).json()
    assert after_stake["my_wallet_balance"] == after_stake["my_wallet_starting"] - 3000

    cancel_resp = client.delete(
        f"/api/v1/leagues/{league['id']}/gameweeks/{gameweek['id']}/predictions/{placed['id']}",
        headers=alice_headers,
    )
    assert cancel_resp.status_code == 204

    after_cancel = client.get(f"/api/v1/leagues/{league['id']}/gameweeks/current", headers=alice_headers).json()
    assert after_cancel["my_wallet_balance"] == after_cancel["my_wallet_starting"]


def test_reset_season_requires_admin_and_starts_fresh(client, alice_headers, bob_headers):
    league = _create_and_join_league(client, alice_headers, bob_headers)

    forbidden = client.post(f"/api/v1/leagues/{league['id']}/reset-season", headers=bob_headers)
    assert forbidden.status_code == 403

    reset = client.post(f"/api/v1/leagues/{league['id']}/reset-season", headers=alice_headers)
    assert reset.status_code == 201
    assert reset.json()["name"] == "Temporada 2"

    season_ranking = client.get(f"/api/v1/leagues/{league['id']}/rankings/season", headers=alice_headers).json()
    assert {row["balance"] for row in season_ranking} == {0}


def test_budget_update_applies_to_next_gameweek(client, alice_headers, bob_headers):
    league = _create_and_join_league(client, alice_headers, bob_headers)
    client.patch(f"/api/v1/leagues/{league['id']}", json={"budget_per_gameweek": 5000}, headers=alice_headers)

    gameweek = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/generate-next", headers=alice_headers
    ).json()
    assert gameweek["budget"] == 5000
    assert gameweek["my_wallet_starting"] == 5000
