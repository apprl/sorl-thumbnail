BEGIN TRANSACTION;
INSERT INTO "apparel_optiontype" VALUES(1,'Gender','Gender (M, F or U)',NULL);
INSERT INTO "apparel_optiontype" VALUES(2,'Shoe Size (EU)','European sizes (numeric)','size');
INSERT INTO "apparel_optiontype" VALUES(3,'Pants (Length)','Length of pants or trousers','size');
INSERT INTO "apparel_optiontype" VALUES(4,'Pants (Width)','Width of pants or trousers','size');
INSERT INTO "apparel_optiontype" VALUES(5,'Color','Color as plain text (in English)',NULL);
INSERT INTO "apparel_optiontype" VALUES(6,'Relative Size','Relative size (X*L, L, M, S, X*S)','size');
COMMIT;
