from pathlib import Path
import sqlite3

import boards


test_db = Path("/tmp/lunatick_board_votes_test.sqlite")
test_db.unlink(missing_ok=True)
boards.DB = str(test_db)
boards.init_boards_db()

boards.create_post("general", "author-a", "Author A", "First post", "First message")
boards.create_post("general", "author-b", "Author B", "Second post", "Second message")
posts = boards.list_posts(limit=10, viewer_hash="member-a")
first_post = next(post for post in posts if post["title"] == "First post")
second_post = next(post for post in posts if post["title"] == "Second post")

assert boards.set_post_vote("member-a", first_post["id"], "up") == (1, 0)
assert boards.set_post_vote("member-a", first_post["id"], "down") == (0, 1)
assert boards.set_post_vote("member-a", first_post["id"], None) == (0, 0)
assert boards.set_post_vote("member-a", first_post["id"], "up") == (1, 0)
assert boards.set_post_vote("member-b", first_post["id"], "up") == (2, 0)
assert boards.set_post_vote("member-a", second_post["id"], "up") == (1, 0)

with sqlite3.connect(test_db) as connection:
    connection.execute("UPDATE board_posts SET created_at=? WHERE id=?", ("2026-01-01 00:00:00", first_post["id"]))
    connection.execute("UPDATE board_posts SET created_at=? WHERE id=?", ("2026-01-02 00:00:00", second_post["id"]))

posts = boards.list_posts(limit=10, viewer_hash="member-a")
first_post = next(post for post in posts if post["title"] == "First post")
assert first_post["upvotes"] == 2
assert first_post["downvotes"] == 0
assert first_post["viewer_vote"] == "up"
assert boards._sort_posts(posts, "Top")[0]["title"] == "First post"
assert boards._sort_posts(posts, "Newest")[0]["title"] == "Second post"

test_db.unlink(missing_ok=True)
print("Board vote persistence and sorting checks passed.")
