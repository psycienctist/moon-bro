-- LunaTicK privacy hardening: prevent email-derived values from being stored as public display names.
-- Existing records were audited with aggregate-only queries before this constraint is applied.

begin;

alter table public.profiles
    add constraint profiles_display_name_not_email_derived
    check (
        position(chr(64) in display_name) = 0
        and (
            email is null
            or lower(trim(display_name)) <> lower(split_part(email, chr(64), 1))
        )
    );

commit;
