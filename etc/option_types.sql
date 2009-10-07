BEGIN TRANSACTION;
INSERT INTO "apparel_optiontype" VALUES(1,'Size','Size Parent Node',NULL,1,10,3,0);
INSERT INTO "apparel_optiontype" VALUES(2,'Shoe Size (EU)','European sizes (numeric)',1,8,9,3,1);
INSERT INTO "apparel_optiontype" VALUES(3,'Pants (Length)','Length of pants or trousers',1,2,3,3,1);
INSERT INTO "apparel_optiontype" VALUES(4,'Pants (Width)','Width of pants or trousers',1,4,5,3,1);
INSERT INTO "apparel_optiontype" VALUES(5,'Relative Size','Relative size (X*L, L, M, S, X*S)',1,6,7,3,1);
INSERT INTO "apparel_optiontype" VALUES(6,'Gender','Gender (M, F or U)',NULL,1,2,2,0);
INSERT INTO "apparel_optiontype" VALUES(7,'Color','Color as plain text (in English)',NULL,1,2,1,0);
COMMIT;
