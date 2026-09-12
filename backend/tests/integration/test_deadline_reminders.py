import uuid
from datetime import timedelta

from app.db.base import utcnow
from app.models.gameweek import Gameweek
from app.services import gameweeks as gameweeks_service


def test_reminder_sent_once_to_members_who_have_not_picked(client, db_session, alice_headers, bob_headers):
    league = client.post("/api/v1/leagues", json={"name": "Reminder League"}, headers=alice_headers).json()
    client.post("/api/v1/leagues/join", json={"invite_code": league["invite_code"]}, headers=bob_headers)

    gameweek = client.post(
        f"/api/v1/leagues/{league['id']}/gameweeks/generate-next", headers=alice_headers
    ).json()
    match = gameweek["matches"][0]
    winner_home = next(o for o in match["odds"] if o["market"] == "winner" and o["selection"] == "home")

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
        headers=alice_headers,
    )

    gw_row = db_session.get(Gameweek, uuid.UUID(gameweek["id"]))
    gw_row.locks_at = utcnow() + timedelta(minutes=90)
    db_session.commit()

    sent = gameweeks_service.send_deadline_reminders(db_session)
    assert sent == 1  # only Bob, who hasn't picked yet

    alice_notifications = client.get("/api/v1/notifications", headers=alice_headers).json()
    bob_notifications = client.get("/api/v1/notifications", headers=bob_headers).json()
    assert not any(n["type"] == "deadline_reminder" for n in alice_notifications)
    assert any(n["type"] == "deadline_reminder" for n in bob_notifications)

    # Firing again is a no-op — the reminder is sent once per gameweek.
    sent_again = gameweeks_service.send_deadline_reminders(db_session)
    assert sent_again == 0
