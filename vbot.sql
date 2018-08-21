CREATE DATABASE  IF NOT EXISTS `vbot`;
USE `vbot`;

CREATE TABLE `votes` (
  `chatid` bigint NOT NULL,
  `messageid` bigint NOT NULL,
  `userid` int NOT NULL,
  `vote` int NOT NULL,
  `hits` tinyint(4) DEFAULT '1' NOT NULL,
  PRIMARY KEY (`chatid`, `messageid`, `userid`)
);

CREATE TABLE `registrationkey` (
  `passphrase` nvarchar(50) NOT NULL
);

CREATE TABLE `admins` (
  `userid` int NOT NULL,
  `username` nvarchar(50) NOT NULL,
  `root` tinyint(4) DEFAULT '0',
  PRIMARY KEY (`userid`),
  UNIQUE KEY `username` (`username`)
);

CREATE TABLE `groups` (
  `groupid` bigint NOT NULL,
  `groupname` nvarchar(50) NOT NULL,
  PRIMARY KEY (`groupid`)
);

CREATE TABLE `messages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `userid` int NOT NULL,
  `messagedate` datetime NOT NULL,
  `groupid` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `userid` (`userid`),
  KEY `groupid` (`groupid`),
  CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`userid`) REFERENCES `admins` (`userid`),
  CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`groupid`) REFERENCES `groups` (`groupid`)
);

DELIMITER //
CREATE DEFINER=`root`@`localhost` PROCEDURE `usp_getadmins`()
BEGIN
	SELECT userid FROM `admins`;
END;
//

CREATE DEFINER=`root`@`localhost` PROCEDURE `usp_getpassphrase`()
BEGIN
	SELECT passphrase FROM `registrationkey`;
END;
//

CREATE DEFINER=`root`@`localhost` PROCEDURE `usp_saveadmin`(uid int, uname varchar(50))
BEGIN
	SET @userid = (SELECT userid FROM `admins` WHERE userid = uid);

    /*admin upsert*/
    INSERT IGNORE INTO `admins` (userid, username)
	VALUES (uid, uname);

	UPDATE `admins`
	SET username = uname
	WHERE userid = uid AND username <> uname;
END;
//

CREATE DEFINER=`root`@`localhost` PROCEDURE `usp_savemessages`(uid int, uname nvarchar(50), gid bigint, gname varchar(50), messagedate datetime)
BEGIN
    /*Group upsert*/
    INSERT IGNORE INTO `groups` (groupid, groupname)
	VALUES (gid, gname);

	UPDATE `groups`
	SET groupname = gname
	WHERE groupid = gid AND groupname <> gname;

	/*Keep usernames updated*/
	UPDATE `admins`
	SET username = uname
	WHERE userid = uid AND username <> uname;
    
    INSERT INTO `messages` (userid, messagedate, groupid)
    VALUES (uid, messagedate, gid);
END;
//


CREATE DEFINER=`root`@`localhost` PROCEDURE `usp_getmessagereport`(uid int, days int)
BEGIN
	SELECT @userid:=userid, @root:=root FROM admins WHERE userid = uid;
    
    IF @root = 1 THEN
		SELECT username as 'USERNAME', g.groupname as 'GROUP', DATE_FORMAT(messagedate,'%m/%d/%Y') AS `DATE`,  COUNT(1) AS `MESSAGES`
		FROM `messages` m
		JOIN `admins` a ON m.userid = a.userid
        JOIN vbot.`groups` g ON m.groupid = g.groupid
		WHERE messagedate >= DATE_ADD(CURDATE(), INTERVAL days*-1 DAY)
		GROUP BY username, g.groupname, DATE_FORMAT(messagedate,'%m/%d/%Y');
	ELSE
		SELECT DATE_FORMAT(messagedate,'%m/%d/%Y') AS `DATE`, g.groupname as 'GROUP',  COUNT(1) AS `MESSAGES`
		FROM `messages` m
		JOIN `admins` a ON m.userid = a.userid
        JOIN vbot.`groups` g ON m.groupid = g.groupid
		WHERE m.userid = @userid and
				messagedate >= DATE_ADD(CURDATE(), INTERVAL days*-1 DAY)
		GROUP BY DATE_FORMAT(messagedate,'%m/%d/%Y'), g.groupname;
	END IF;
END;
//

CREATE DEFINER=`root`@`localhost` PROCEDURE `usp_savevote`(pchatid bigint, pmessageid bigint, puserid int, pvote int)
BEGIN
    SET @hits := 1;
	INSERT INTO `votes`
    (chatid, messageid, userid, vote)
    VALUES
        (pchatid, pmessageid, puserid, pvote)
    ON DUPLICATE KEY UPDATE
        hits = @hits := hits + 1,
        vote = pvote;
    SELECT @hits as hits;
END;
//

CREATE DEFINER=`root`@`localhost` PROCEDURE `usp_getvoters`(pchatid bigint, pmessageid bigint)
BEGIN
    SELECT userid, vote, hits
    FROM `votes`
    WHERE chatid = pchatid AND messageid = pmessageid;
END;
//