-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Dec 11, 2025 at 06:25 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `chat_distribution_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `chatrooms`
--

CREATE TABLE `chatrooms` (
  `room_id` bigint(20) NOT NULL,
  `room_name` varchar(100) NOT NULL,
  `type` enum('group','direct','','') NOT NULL,
  `created_by` bigint(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `chatrooms`
--

INSERT INTO `chatrooms` (`room_id`, `room_name`, `type`, `created_by`, `created_at`) VALUES
(1, '#ngobrol-ajah', 'group', 1, '2025-12-10 06:56:36'),
(2, 'direct_1_2', 'direct', 1, '2025-12-10 13:28:41');

-- --------------------------------------------------------

--
-- Table structure for table `friends`
--

CREATE TABLE `friends` (
  `user_id` bigint(20) NOT NULL,
  `friend_id` bigint(20) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `friends`
--

INSERT INTO `friends` (`user_id`, `friend_id`, `created_at`) VALUES
(1, 2, '2025-12-10 09:41:08'),
(2, 1, '2025-12-10 09:41:08');

-- --------------------------------------------------------

--
-- Table structure for table `messages`
--

CREATE TABLE `messages` (
  `message_id` bigint(20) NOT NULL,
  `publisher_msg_id` varchar(64) NOT NULL,
  `room_id` bigint(20) NOT NULL,
  `sender_id` bigint(20) DEFAULT NULL,
  `seq` int(11) DEFAULT NULL,
  `content` text NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `broker_received_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `messages`
--

INSERT INTO `messages` (`message_id`, `publisher_msg_id`, `room_id`, `sender_id`, `seq`, `content`, `created_at`, `broker_received_at`) VALUES
(1, '5f76fd22-6f1c-42c2-aa8b-69a96bb935a4', 1, 1, 0, 'Haloo teman temannn', '2025-12-10 06:56:48', '2025-12-10 06:56:48'),
(2, '16259699-5532-4af9-a258-5b7e62f9300c', 1, 1, 0, 'alhamdulillah ini chatnya udah work hehe', '2025-12-10 06:58:52', '2025-12-10 06:58:52'),
(3, 'd543830f-2425-4699-a493-1173f1b83509', 1, 1, 0, 'lah', '2025-12-10 08:43:27', '2025-12-10 08:43:27'),
(4, 'd9424879-347b-4dcc-ae9e-32599746abc0', 1, 1, 0, 'lah kok gini si', '2025-12-10 08:46:10', '2025-12-10 08:46:10'),
(5, '7137d4ed-b0d1-488e-8a7c-c5072bf9dced', 1, 1, 0, 'alhamdulillah mantap', '2025-12-10 09:09:44', '2025-12-10 09:09:44'),
(6, '95199fed-8aef-40a2-880d-bb7666014d13', 2, 1, 0, 'halo bang assalamualaikum', '2025-12-10 13:28:55', '2025-12-10 13:28:55'),
(7, '20920483-a207-4984-a867-c646c77dbb0f', 2, 2, 0, 'waalaikumussalam', '2025-12-10 13:32:02', '2025-12-10 13:32:02'),
(8, '79f2205d-e986-42ed-a0c9-90a9ac41711d', 2, 1, 0, 'sehat bang?', '2025-12-10 13:32:17', '2025-12-10 13:32:17'),
(9, '253de0ed-58ff-4093-bd21-72ee78df87d5', 2, 2, 0, 'alhamdulillah sehat', '2025-12-10 13:32:38', '2025-12-10 13:32:38'),
(10, 'e024e7b7-01c3-44de-88a8-8de21b0de8c1', 2, 1, 0, 'besok kalo ketemu bisa ga bang? mau bahas sesuatu sih...', '2025-12-10 13:33:16', '2025-12-10 13:33:16'),
(11, '9a05366b-03c9-4e3b-b10f-85a25b2ced28', 2, 2, 0, 'bahas apatuh?', '2025-12-10 13:33:32', '2025-12-10 13:33:32'),
(12, '5a4411c7-e62a-47f8-8da9-b81d8c8458f9', 1, 2, 0, 'Assalamualaikum', '2025-12-10 13:41:49', '2025-12-10 13:41:49'),
(13, '845f16f1-e8d6-4e77-b841-da665c89b54b', 1, 1, 0, 'halo halo selamat datang', '2025-12-10 13:42:02', '2025-12-10 13:42:02'),
(14, '71dcf59d-e6cd-4650-b8b6-bac7aa529ec1', 1, 2, 0, 'hehe iya thanks ya', '2025-12-10 13:45:19', '2025-12-10 13:45:19'),
(15, 'b9b13797-b7b5-4d7e-802b-0ec654e237f9', 1, 1, 0, 'btw kita disini bahas project sister yaa', '2025-12-10 14:12:08', '2025-12-10 14:12:08'),
(16, '492de372-0f87-4ff8-a983-a78c548850c7', 1, 1, 0, 'wduh wak kekirim dua kali rupanya', '2025-12-10 14:12:16', '2025-12-10 14:12:16'),
(18, '30bebbd1-9e08-4985-9aad-220d5551aa21', 2, 1, 0, 'adalah pokoknya', '2025-12-10 14:12:53', '2025-12-10 14:12:53'),
(19, 'f9fecf8c-8059-4d6c-9aa3-76def12e38ea', 1, 1, 0, 'halo ', '2025-12-10 14:29:18', '2025-12-10 14:29:18'),
(20, 'f69f8cc2-b678-454e-b451-afa16a632948', 1, 2, 0, 'hai', '2025-12-10 14:30:16', '2025-12-10 14:30:16'),
(21, '39c73739-e4cf-4531-9c4b-1e9c04e3b4a1', 2, 1, 0, 'test', '2025-12-10 14:31:05', '2025-12-10 14:31:05'),
(22, '1cdacb26-b86d-4552-8190-4151fa2a075a', 2, 2, 0, 'lahh', '2025-12-10 14:31:24', '2025-12-10 14:31:24'),
(23, 'b1bb76de-021e-43f8-9241-4046ed2b10d2', 1, 1, 0, 'hai juga', '2025-12-10 23:29:37', '2025-12-10 23:29:37'),
(24, '0ced2c42-f3da-44cb-9cc9-dde16cdeba15', 1, 1, 0, 'tes tos', '2025-12-10 23:29:43', '2025-12-10 23:29:43'),
(25, '5465d20b-32bf-4a12-a18c-f95bd3a6d44d', 1, 1, 0, 'assalamualaikum', '2025-12-10 23:42:44', '2025-12-10 23:42:44'),
(26, '862f3033-9803-4dc9-ace4-8f858aea5003', 1, 1, 0, 'waalaikumsalam', '2025-12-10 23:43:01', '2025-12-10 23:43:01'),
(27, '95c02a44-459b-4b7e-b8b6-df1f5cb7085b', 2, 1, 0, 'test', '2025-12-10 23:44:11', '2025-12-10 23:44:11'),
(28, '06cfac1e-62b8-4ca0-8a8a-ef70acc35379', 1, 1, 0, 'tes', '2025-12-10 23:45:09', '2025-12-10 23:45:09'),
(29, '564c97e3-5d45-4a36-afbd-91f0b2ebe8b3', 1, 1, 0, 'hai', '2025-12-10 23:57:07', '2025-12-10 23:57:07'),
(30, '8ecd7202-081f-466c-a2f9-7a8dcd38fbe7', 1, 1, 0, 'lah', '2025-12-10 23:57:12', '2025-12-10 23:57:12'),
(31, '9b4a0b88-1b01-4790-a237-908f2d1c2e67', 1, 1, 0, 'alhamdulillah', '2025-12-10 23:57:16', '2025-12-10 23:57:16'),
(32, '04f6af09-5cfe-4582-9be0-2cb1830dc972', 2, 1, 0, 'hai', '2025-12-10 23:57:20', '2025-12-10 23:57:20'),
(33, '2ad448e0-2e44-4b8a-b2e9-88156ff9cd1c', 2, 1, 0, 'alhamdulillah', '2025-12-10 23:57:24', '2025-12-10 23:57:24'),
(34, '2d416b16-c441-4cd0-82b7-8ad8296551f8', 2, 2, 0, 'ea', '2025-12-11 04:46:54', '2025-12-11 04:46:54'),
(35, 'cdf8a179-e409-452b-aa78-36b2c3163bdf', 2, 1, 0, 'ea', '2025-12-11 04:46:54', '2025-12-11 04:46:54');

-- --------------------------------------------------------

--
-- Table structure for table `notifications`
--

CREATE TABLE `notifications` (
  `notif_id` bigint(20) NOT NULL,
  `message_id` bigint(20) NOT NULL,
  `receiver_id` bigint(20) NOT NULL,
  `status` enum('sent','failed') DEFAULT 'sent',
  `sent_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `room_members`
--

CREATE TABLE `room_members` (
  `room_id` bigint(20) NOT NULL,
  `user_id` bigint(20) NOT NULL,
  `joined_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `room_members`
--

INSERT INTO `room_members` (`room_id`, `user_id`, `joined_at`) VALUES
(1, 1, '2025-12-10 06:56:36'),
(1, 2, '2025-12-10 13:41:32'),
(2, 1, '2025-12-10 13:28:41'),
(2, 2, '2025-12-10 13:28:41');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_id` bigint(20) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `status` enum('online','offline') DEFAULT 'offline',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_id`, `username`, `email`, `password`, `status`, `created_at`, `updated_at`) VALUES
(1, 'Hajjid Rafi Mumtaz', 'rafimumtaz86@gmail.com', 'scrypt:32768:8:1$YTRXJMI7Kde1n5UI$aa071d12dfb6b476da0fe2956bae4667156007d6f67a833ae8e9c76a0d4a8f600ffcf21de6f4261164fc24f36b2b9dcf3a6ee53250b6cd9d5f7ad7511dd0f00e', 'online', '2025-12-10 05:27:35', '2025-12-11 04:45:33'),
(2, 'Tria Yunita Krismiyanto', 'triayunita07@gmail.com', 'scrypt:32768:8:1$7GeEh2keRJLDyqJo$8f4bc4dcadd850cc54d86fa45cc424f4717b08f287a99ce4e593ce8193f338cf0981743bc6a55d70cd45735cdfb30ba1ce0a2ffafb9b41d3b0a0fb581e17c64d', 'online', '2025-12-10 09:12:58', '2025-12-11 00:48:23');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `chatrooms`
--
ALTER TABLE `chatrooms`
  ADD PRIMARY KEY (`room_id`),
  ADD KEY `created_by` (`created_by`);

--
-- Indexes for table `friends`
--
ALTER TABLE `friends`
  ADD PRIMARY KEY (`user_id`,`friend_id`),
  ADD KEY `friend_id` (`friend_id`);

--
-- Indexes for table `messages`
--
ALTER TABLE `messages`
  ADD PRIMARY KEY (`message_id`),
  ADD UNIQUE KEY `uniq_publisher_msg_id` (`publisher_msg_id`),
  ADD KEY `room_id` (`room_id`),
  ADD KEY `sender_id` (`sender_id`),
  ADD KEY `idx_room_seq` (`room_id`,`seq`),
  ADD KEY `idx_room_created` (`room_id`,`created_at`);

--
-- Indexes for table `notifications`
--
ALTER TABLE `notifications`
  ADD PRIMARY KEY (`notif_id`),
  ADD KEY `message_id` (`message_id`),
  ADD KEY `receiver_id` (`receiver_id`);

--
-- Indexes for table `room_members`
--
ALTER TABLE `room_members`
  ADD PRIMARY KEY (`room_id`,`user_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `chatrooms`
--
ALTER TABLE `chatrooms`
  MODIFY `room_id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `messages`
--
ALTER TABLE `messages`
  MODIFY `message_id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=36;

--
-- AUTO_INCREMENT for table `notifications`
--
ALTER TABLE `notifications`
  MODIFY `notif_id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `user_id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `chatrooms`
--
ALTER TABLE `chatrooms`
  ADD CONSTRAINT `chatrooms_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

--
-- Constraints for table `friends`
--
ALTER TABLE `friends`
  ADD CONSTRAINT `friends_friend_fk` FOREIGN KEY (`friend_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `friends_user_fk` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `messages`
--
ALTER TABLE `messages`
  ADD CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `chatrooms` (`room_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`sender_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL;

--
-- Constraints for table `notifications`
--
ALTER TABLE `notifications`
  ADD CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`message_id`) REFERENCES `messages` (`message_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `notifications_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `room_members`
--
ALTER TABLE `room_members`
  ADD CONSTRAINT `room_members_ibfk_1` FOREIGN KEY (`room_id`) REFERENCES `chatrooms` (`room_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `room_members_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
