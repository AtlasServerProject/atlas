CREATE TABLE atlas_web.support_tickets (
 id UUID PRIMARY KEY, order_id UUID NOT NULL UNIQUE REFERENCES atlas_web.orders(id),
 user_id UUID NOT NULL REFERENCES atlas_web.users(id), title VARCHAR(120) NOT NULL,
 status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN','IN_PROGRESS','WAITING_CUSTOMER','RESOLVED')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX support_customer ON atlas_web.support_tickets(user_id,updated_at DESC);
CREATE INDEX support_queue ON atlas_web.support_tickets(status,updated_at DESC);
CREATE TABLE atlas_web.support_messages (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 ticket_id UUID NOT NULL REFERENCES atlas_web.support_tickets(id), author UUID NOT NULL REFERENCES atlas_web.users(id),
 kind TEXT NOT NULL CHECK(kind IN ('CUSTOMER','STAFF','STATUS')),
 body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 4000), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX support_conversation ON atlas_web.support_messages(ticket_id,id);
GRANT SELECT,INSERT,UPDATE ON atlas_web.support_tickets TO atlas_api_runtime;
GRANT SELECT,INSERT ON atlas_web.support_messages TO atlas_api_runtime;
GRANT USAGE,SELECT ON SEQUENCE atlas_web.support_messages_id_seq TO atlas_api_runtime;
UPDATE atlas_web.system_metadata SET schema_generation=9 WHERE id=1;
