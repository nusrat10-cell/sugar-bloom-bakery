from database import get_supabase
from security import hash_password


def run_seed():
    db = get_supabase()

    demo_users = [
        {
            "email": "admin1@bakery.com",
            "username": "admin1",
            "full_name": "Admin One",
            "password_hash": hash_password("pass1234"),
            "role": "admin",
        },
        {
            "email": "admin2@bakery.com",
            "username": "admin2",
            "full_name": "Admin Two",
            "password_hash": hash_password("pass1234"),
            "role": "admin",
        },
        {
            "email": "user1@bakery.com",
            "username": "user1",
            "full_name": "User One",
            "password_hash": hash_password("user1234"),
            "role": "user",
        },
        {
            "email": "user2@bakery.com",
            "username": "user2",
            "full_name": "User Two",
            "password_hash": hash_password("user1234"),
            "role": "user",
        },
        {
            "email": "user3@bakery.com",
            "username": "user3",
            "full_name": "User Three",
            "password_hash": hash_password("user1234"),
            "role": "user",
        },
    ]

    users_by_username = {}
    for u in demo_users:
        existing = db.table("users").select("*").eq("email", u["email"]).limit(1).execute()
        if existing.data:
            users_by_username[u["username"]] = existing.data[0]
        else:
            inserted = db.table("users").insert(u).execute()
            users_by_username[u["username"]] = inserted.data[0]

    owner = users_by_username["user1"]
    member_edit = users_by_username["user2"]
    member_create_only = users_by_username["user3"]

    group_name = "Cake Team"
    existing_groups = (
        db.table("groups").select("*").eq("name", group_name).eq("owner_id", owner["id"]).limit(1).execute()
    )
    if existing_groups.data:
        group = existing_groups.data[0]
    else:
        group = (
            db.table("groups")
            .insert(
                {
                    "name": group_name,
                    "description": "Shared group for bakery items",
                    "owner_id": owner["id"],
                }
            )
            .execute()
            .data[0]
        )

    memberships = [
        {
            "group_id": group["id"],
            "user_id": member_edit["id"],
            "can_create": True,
            "can_update": True,
            "can_assign": True,
        },
        {
            "group_id": group["id"],
            "user_id": member_create_only["id"],
            "can_create": True,
            "can_update": False,
            "can_assign": False,
        },
    ]
    for m in memberships:
        found = (
            db.table("group_members")
            .select("id")
            .eq("group_id", m["group_id"])
            .eq("user_id", m["user_id"])
            .limit(1)
            .execute()
        )
        if not found.data:
            db.table("group_members").insert(m).execute()

    sample_products = [
        {
            "owner_id": owner["id"],
            "group_id": group["id"],
            "assigned_to": member_edit["id"],
            "name": "Chocolate Cake",
            "description": "Simple chocolate cake",
            "category": "Cake",
            "price": 15.00,
            "stock": 10,
        },
        {
            "owner_id": owner["id"],
            "group_id": group["id"],
            "assigned_to": member_create_only["id"],
            "name": "Vanilla Cupcake",
            "description": "Vanilla cupcake batch",
            "category": "Cupcake",
            "price": 5.00,
            "stock": 20,
        },
        {
            "owner_id": member_edit["id"],
            "group_id": None,
            "assigned_to": None,
            "name": "Butter Cookies",
            "description": "Homemade butter cookies",
            "category": "Cookies",
            "price": 8.00,
            "stock": 12,
        },
    ]

    existing_prods = db.table("products").select("name").execute().data
    existing_names = {p["name"] for p in existing_prods}
    for prod in sample_products:
        if prod["name"] not in existing_names:
            db.table("products").insert(prod).execute()

    print("Seed complete!")
    print("Admins:", users_by_username["admin1"]["id"], users_by_username["admin2"]["id"])
    print(
        "Users:",
        users_by_username["user1"]["id"],
        users_by_username["user2"]["id"],
        users_by_username["user3"]["id"],
    )
    print("Group ID:", group["id"])


if __name__ == "__main__":
    run_seed()