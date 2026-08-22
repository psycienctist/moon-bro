-- Public Cosmic Cards remain visually present by default. This flag controls only
-- whether the owner's derived cosmic values are rendered on their public card.
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS public_card_values_visible boolean NOT NULL DEFAULT true;

COMMENT ON COLUMN public.profiles.public_card_values_visible IS
    'Whether derived Cosmic Card values may be displayed on public profile cards; the card frame remains visible regardless.';
