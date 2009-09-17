BEGIN TRANSACTION;
CREATE TABLE "apparel_option" (
    "id" integer NOT NULL PRIMARY KEY,
    "value" varchar(255) NOT NULL,
    "option_type_id" integer NOT NULL REFERENCES "apparel_optiontype" ("id"),
    "sort_order" integer NOT NULL,
    UNIQUE ("option_type_id", "value")
);
CREATE INDEX "apparel_option_option_type_id" ON "apparel_option" ("option_type_id");
COMMIT;
