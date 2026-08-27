from pathlib import Path

import reading_requests as readings


test_db = Path("/tmp/lunatick_reading_requests_test.sqlite")
test_db.unlink(missing_ok=True)
readings.DB = str(test_db)
readings._using_supabase_backend = lambda: False


def set_member(member_id: str, display_name: str) -> None:
    readings._member_id = lambda: member_id
    readings._display_name = lambda: display_name
    readings._avatar = lambda: "🌙"


readings.init_reading_requests_db()
set_member("seeker", "Seeker")
request_id = readings.create_request("Understanding a transit", "A private detail for the matched reader.")
open_request = readings.list_open_requests()[0]
assert open_request["id"] == request_id
assert "private_context" not in open_request

set_member("reader", "Reader")
readings.save_reader_profile("Natal charts", "Gentle, reflective readings.", True)
assert readings.get_reader_profile()["is_available"] is True
assert readings.accept_request(request_id) is True
matched = readings.get_request(request_id)
assert matched["status"] == "matched"
assert matched["reader_id"] == "reader"
assert readings.send_message(request_id, "Thank you for trusting me with this.") is True

set_member("seeker", "Seeker")
assert readings.list_messages(request_id)[0]["content"] == "Thank you for trusting me with this."
assert readings.send_message(request_id, "Thank you.") is True
assert readings.close_request(request_id) is True
assert readings.get_request(request_id)["status"] == "closed"

set_member("outsider", "Outsider")
assert readings.list_messages(request_id) == []
assert readings.send_message(request_id, "Not allowed") is False

test_db.unlink(missing_ok=True)
print("Reading request matching and private-message checks passed.")
