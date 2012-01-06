CREATE DATABASE apparelrow;
CREATE USER 'apparelrow'@'%(db_client_host)s' IDENTIFIED BY 'ashwe3';
GRANT ALL PRIVILEGES ON apparelrow.* TO 'apparelrow'@'%(db_client_host)s';
