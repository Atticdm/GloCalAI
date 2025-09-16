CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO app_user (id, email, password_hash, role)
VALUES (
    '11111111-2222-3333-4444-555555555555',
    'admin@glocal.ai',
    crypt('admin12345', gen_salt('bf')),
    'admin'
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO voice_profile (id, name, provider, provider_params)
VALUES
    (
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeee0001',
        'Female 25-35',
        'xtts',
        '{"gender": "female", "age_range": "25-35", "style": "bright"}'::jsonb
    ),
    (
        'aaaaaaaa-bbbb-cccc-dddd-eeeeeeee0002',
        'Male 25-35',
        'xtts',
        '{"gender": "male", "age_range": "25-35", "style": "bright"}'::jsonb
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO project (id, owner_id, name)
VALUES (
    'dddddddd-1111-2222-3333-444444444444',
    '11111111-2222-3333-4444-555555555555',
    'Demo Project'
)
ON CONFLICT (id) DO NOTHING;
