-- Database Schema for Distributed Chat Application

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Table structure for table `USER`
--

CREATE TABLE `USER` (
  `user_id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `password` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `status` enum('online','offline') COLLATE utf8mb4_general_ci DEFAULT 'offline',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Table structure for table `CHATROOM`
--

CREATE TABLE `CHATROOM` (
  `room_id` bigint NOT NULL AUTO_INCREMENT,
  `room_name` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `created_by` bigint DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`room_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `chatroom_created_by_fk` FOREIGN KEY (`created_by`) REFERENCES `USER` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Table structure for table `MESSAGES`
--

CREATE TABLE `MESSAGES` (
  `message_id` bigint NOT NULL AUTO_INCREMENT,
  `publisher_msg_id` varchar(64) COLLATE utf8mb4_general_ci NOT NULL,
  `room_id` bigint NOT NULL,
  `sender_id` bigint DEFAULT NULL,
  `seq` int DEFAULT NULL,
  `content` text COLLATE utf8mb4_general_ci NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `broker_received_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`message_id`),
  UNIQUE KEY `uniq_publisher_msg_id` (`publisher_msg_id`),
  KEY `room_id` (`room_id`),
  KEY `sender_id` (`sender_id`),
  KEY `idx_room_seq` (`room_id`,`seq`),
  KEY `idx_room_created` (`room_id`,`created_at`),
  CONSTRAINT `messages_room_fk` FOREIGN KEY (`room_id`) REFERENCES `CHATROOM` (`room_id`) ON DELETE CASCADE,
  CONSTRAINT `messages_sender_fk` FOREIGN KEY (`sender_id`) REFERENCES `USER` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Table structure for table `NOTIFICATION`
--

CREATE TABLE `NOTIFICATION` (
  `notif_id` bigint NOT NULL AUTO_INCREMENT,
  `message_id` bigint NOT NULL,
  `receiver_id` bigint NOT NULL,
  `status` enum('sent','failed') COLLATE utf8mb4_general_ci DEFAULT 'sent',
  `sent_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`notif_id`),
  KEY `message_id` (`message_id`),
  KEY `receiver_id` (`receiver_id`),
  CONSTRAINT `notif_message_fk` FOREIGN KEY (`message_id`) REFERENCES `MESSAGES` (`message_id`) ON DELETE CASCADE,
  CONSTRAINT `notif_receiver_fk` FOREIGN KEY (`receiver_id`) REFERENCES `USER` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Table structure for table `ROOM_MEMBERS`
--

CREATE TABLE `ROOM_MEMBERS` (
  `room_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  `joined_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`room_id`,`user_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `members_room_fk` FOREIGN KEY (`room_id`) REFERENCES `CHATROOM` (`room_id`) ON DELETE CASCADE,
  CONSTRAINT `members_user_fk` FOREIGN KEY (`user_id`) REFERENCES `USER` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
