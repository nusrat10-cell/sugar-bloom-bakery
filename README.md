# Sugar Bloom Bakery

A full-stack multi-user bakery management application built with React, TypeScript, FastAPI, and Supabase.

## Features
- JWT authentication with short-lived access tokens and refresh token rotation/revocation
- Password hashing with bcrypt and a server-side pepper
- Role-based access control (RBAC) for `user` and `admin` roles
- Shared group (`Cake Team`) with member permissions (`can_create`, `can_update`, `can_assign`) and owner-only group management
- Admin dashboard with overview stats, user management, content moderation, activity logs, security view, and CSV exports

## Demo Accounts (IDs and Roles Only)
- **Admin (`admin1` / `admin1@bakery.com`)**: `48066d4e-2126-4670-8caa-f651f63aee71` (`role: admin`)
- **Admin (`admin2` / `admin2@bakery.com`)**: `1de85d03-cf7e-455b-990f-ed304e4aec08` (`role: admin`)
- **User (`user1` / `user1@bakery.com`)**: `2fe4539e-60f6-44d9-accb-b26f61204364` (`role: user`, owner of `Cake Team`)
- **User (`user2` / `user2@bakery.com`)**: `06abb800-a884-48d6-bbbe-aac156812707` (`role: user`, member of `Cake Team`: `can_create=true`, `can_update=true`, `can_assign=true`)
- **User (`user3` / `user3@bakery.com`)**: `c83af8ab-d1f6-4bfa-ac23-5a50139330d5` (`role: user`, member of `Cake Team`: `can_create=true`, `can_update=false`, `can_assign=false`)

## Sample Data & Shared Group
- **Shared Group**: `Cake Team` (`a498dd36-b214-4a7f-ae3a-be0ac031568b`), owned by `user1`.
- **Sample Products**: `Chocolate Cake`, `Vanilla Cupcake`, and `Butter Cookies`.