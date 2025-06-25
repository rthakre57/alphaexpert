CREATE DATABASE IF NOT EXISTS ai_questions;
USE ai_questions;

CREATE TABLE IF NOT EXISTS classes (
    class_id INT AUTO_INCREMENT PRIMARY KEY,
    class_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS subjects (
    subject_id INT AUTO_INCREMENT PRIMARY KEY,
    class_id INT,
    subject_name VARCHAR(255) NOT NULL,
    FOREIGN KEY (class_id) REFERENCES classes(class_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS topics (
    topic_id INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT,
    topic_name VARCHAR(255) NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS questions (
    question_id INT AUTO_INCREMENT PRIMARY KEY,
    topic_id INT,
    question_text TEXT NOT NULL,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    mobile VARCHAR(20),
    username VARCHAR(100) UNIQUE,
    password VARCHAR(100)
);