create table fonts (
  font_id SERIAL PRIMARY KEY,
  fname text,
  data bytea,
  description text,
  downloads int,
  auth_id text
);

create table users (
  user_id SERIAL PRIMARY KEY,
  auth_id text,
  bio text
);