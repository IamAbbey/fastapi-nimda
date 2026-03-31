BEGIN;

CREATE TABLE regions (
    code CHAR(3) PRIMARY KEY,
    name VARCHAR(9) NOT NULL
);

INSERT INTO regions (code, name)
VALUES
    ('002', 'Africa'),
    ('009', 'Oceania'),
    ('010', 'Antarctic'),
    ('019', 'Americas'),
    ('142', 'Asia'),
    ('150', 'Europe');

COMMIT;