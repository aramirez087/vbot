CREATE DATABASE  IF NOT EXISTS `vbot`;
USE `vbot`;


DROP TABLE IF EXISTS `admins`;
CREATE TABLE `admins` (
  `userid` mediumint(9) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `root` tinyint(4) DEFAULT '0',
  PRIMARY KEY (`userid`),
  UNIQUE KEY `username` (`username`)
);


DROP TABLE IF EXISTS `groups`;
CREATE TABLE `groups` (
  `groupid` mediumint(9) NOT NULL AUTO_INCREMENT,
  `groupname` varchar(50) NOT NULL,
  PRIMARY KEY (`groupid`)
);


DROP TABLE IF EXISTS `messages`;
CREATE TABLE `messages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `userid` mediumint(9) NOT NULL,
  `messagedate` datetime NOT NULL,
  `messagetext` nvarchar(4096) NOT NULL,
  `groupid` mediumint(9) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `userid` (`userid`),
  KEY `groupid` (`groupid`),
  CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`userid`) REFERENCES `admins` (`userid`),
  CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`groupid`) REFERENCES `groups` (`groupid`)
);


DELIMITER //
CREATE DEFINER=`root`@`localhost` PROCEDURE `usp_getadmins`()
BEGIN
	select username from admins;
END;
//


DELIMITER //
CREATE DEFINER=`root`@`localhost` PROCEDURE `usp_savemessages`(uname varchar(50), messagedate datetime, messagetext nvarchar(4096), gname varchar(50))
BEGIN
	SET @userid = (SELECT userid FROM admins WHERE username = uname);
	SET @groupid = (SELECT groupid FROM `groups` WHERE groupname = gname);
    
    /*insert new group if doesn't exist*/
    IF (@groupid IS NULL) THEN
		INSERT INTO `groups` (groupname) VALUES (gname);
        SET @groupid = (SELECT LAST_INSERT_ID());
	END IF;
    
    INSERT INTO messages (userid, messagedate, messagetext, groupid)
    VALUES (@userid, messagedate, messagetext, @groupid);
END;
//



DELIMITER //
CREATE DEFINER=`root`@`localhost` PROCEDURE `usp_getmessagereport`(uname varchar(50), days int)
BEGIN
	SELECT @userid:=userid, @r:=root FROM admins WHERE username = uname;
    
    IF @r = 1 THEN
		SELECT username as 'USERNAME', g.groupname as 'GROUP', DATE_FORMAT(messagedate,'%m/%d/%Y') AS `DATE`,  COUNT(1) AS `MESSAGES`
		FROM messages m
		JOIN admins a ON m.userid = a.userid
        JOIN vbot.groups g ON m.groupid = g.groupid 
		WHERE messagedate >= DATE_ADD(CURDATE(), INTERVAL days*-1 DAY)
		GROUP BY username, g.groupname, DATE_FORMAT(messagedate,'%m/%d/%Y');
	ELSE
		SELECT DATE_FORMAT(messagedate,'%m/%d/%Y') AS `DATE`, g.groupname as 'GROUP',  COUNT(1) AS `MESSAGES`
		FROM messages m
		JOIN admins a ON m.userid = a.userid
        JOIN vbot.groups g ON m.groupid = g.groupid
		WHERE m.userid = @userid and
				messagedate >= DATE_ADD(CURDATE(), INTERVAL days*-1 DAY)
		GROUP BY DATE_FORMAT(messagedate,'%m/%d/%Y'), g.groupname;
	END IF;
END;
//
