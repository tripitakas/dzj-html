# ************************************************************
# Sequel Pro SQL dump
# Version 4541
#
# http://www.sequelpro.com/
# https://github.com/sequelpro/sequelpro
#
# Host: 127.0.0.1 (MySQL 5.5.5-10.3.9-MariaDB)
# Database: tripitaka
# Generation Time: 2018-12-18 06:04:33 +0000
# ************************************************************


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;



# Dump of table t_user
# ------------------------------------------------------------

DROP TABLE IF EXISTS `t_user`;

CREATE TABLE `t_user` (
  `id` char(16) NOT NULL COMMENT '用户ID',
  `name` varchar(20) NOT NULL COMMENT '姓名',
  `email` varchar(80) NOT NULL COMMENT '邮箱',
  `phone` int(11) unsigned NOT NULL DEFAULT 0 COMMENT '手机号',
  `password` char(16) NOT NULL COMMENT '密码MD5',
  `create_time` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00' COMMENT '注册时间',
  `last_time` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00' COMMENT '访问时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';



# Dump of table t_authority
# ------------------------------------------------------------

DROP TABLE IF EXISTS `t_authority`;

CREATE TABLE `t_authority` (
  `user_id` char(16) NOT NULL COMMENT '用户ID',
  `cut_proof` tinyint(1) NOT NULL DEFAULT 0 COMMENT '切分校对员',
  `cut_review` tinyint(1) NOT NULL DEFAULT 0 COMMENT '切分审定员',
  `text_proof` tinyint(1) NOT NULL DEFAULT 0 COMMENT '文字校对员',
  `text_review` tinyint(1) NOT NULL DEFAULT 0 COMMENT '文字审定员',
  `text_expert` tinyint(1) NOT NULL DEFAULT 0 COMMENT '文字专家',
  `fmt_proof` tinyint(1) NOT NULL DEFAULT 0 COMMENT '格式标注员',
  `fmt_review` tinyint(1) NOT NULL DEFAULT 0 COMMENT '格式审定员',
  `task_mgr` tinyint(1) NOT NULL DEFAULT 0 COMMENT '任务管理员',
  `data_mgr` tinyint(1) NOT NULL DEFAULT 0 COMMENT '数据管理员',
  `manager` tinyint(1) NOT NULL DEFAULT 0 COMMENT '超级管理员',
  PRIMARY KEY (`user_id`),
  CONSTRAINT `t_authority_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `t_user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPACT COMMENT='用户权限表';



# Dump of table t_op_log
# ------------------------------------------------------------

DROP TABLE IF EXISTS `t_op_log`;

CREATE TABLE `t_op_log` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增id',
  `type` varchar(20) NOT NULL COMMENT '操作类型',
  `user_id` char(16) DEFAULT NULL COMMENT '用户ID',
  `file_id` varchar(24) DEFAULT NULL COMMENT '文件ID',
  `ip` int(10) unsigned NOT NULL COMMENT 'IP地址',
  `context` varchar(80) DEFAULT '' COMMENT '操作内容',
  `create_time` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00' COMMENT '记录创建时间',
  PRIMARY KEY (`id`),
  KEY `k_type` (`type`),
  KEY `k_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPACT COMMENT='操作记录表';





/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
