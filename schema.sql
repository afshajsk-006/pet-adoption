-- Pet Adoption Management System - Database Schema
-- Run this file to set up the database

CREATE DATABASE IF NOT EXISTS pet_adoption CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pet_adoption;

-- Admins table
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Pets table
CREATE TABLE IF NOT EXISTS pets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    species VARCHAR(50) NOT NULL,
    breed VARCHAR(100),
    age DECIMAL(4,1),
    gender ENUM('Male', 'Female', 'Unknown') DEFAULT 'Unknown',
    description TEXT,
    status ENUM('available', 'adopted') DEFAULT 'available',
    added_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Adopters table
CREATE TABLE IF NOT EXISTS adopters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20),
    address TEXT,
    registered_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Adoption Requests table
CREATE TABLE IF NOT EXISTS adoption_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pet_id INT NOT NULL,
    adopter_id INT NOT NULL,
    request_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    resolved_date DATETIME,
    FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
    FOREIGN KEY (adopter_id) REFERENCES adopters(id) ON DELETE CASCADE
);

-- Notices table
CREATE TABLE IF NOT EXISTS notices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    posted_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    admin_id INT,
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(100) NOT NULL UNIQUE,
    value TEXT
);

-- Default admin: email=admin@petadopt.com, password=admin123
-- The real password hash is set automatically by app.py on first startup.
-- Inserting a dummy row here; app.py will overwrite the hash on launch.
INSERT INTO admins (name, email, password_hash) VALUES (
    'Admin',
    'admin@petadopt.com',
    'PLACEHOLDER'
) ON DUPLICATE KEY UPDATE email=email;

-- Default settings
INSERT INTO settings (`key`, value) VALUES ('org_name', 'PawsHome Adoption Center') ON DUPLICATE KEY UPDATE `key`=`key`;

-- Sample pets
INSERT INTO pets (name, species, breed, age, gender, description, status) VALUES
('Buddy', 'Dog', 'Golden Retriever', 2.0, 'Male', 'Friendly and energetic golden retriever who loves to play fetch.', 'available'),
('Whiskers', 'Cat', 'Persian', 3.5, 'Female', 'Calm and affectionate Persian cat, great with kids.', 'available'),
('Max', 'Dog', 'German Shepherd', 4.0, 'Male', 'Loyal and intelligent German Shepherd, well trained.', 'available'),
('Luna', 'Cat', 'Siamese', 1.5, 'Female', 'Playful Siamese kitten, very vocal and social.', 'available'),
('Charlie', 'Dog', 'Beagle', 3.0, 'Male', 'Curious and merry Beagle, loves outdoor adventures.', 'available'),
('Bella', 'Rabbit', 'Holland Lop', 1.0, 'Female', 'Sweet Holland Lop rabbit, very gentle and easy to care for.', 'available');

-- Sample adopters
INSERT INTO adopters (name, email, phone, address) VALUES
('John Smith', 'john.smith@email.com', '555-0101', '123 Oak Street, Springfield'),
('Sarah Johnson', 'sarah.j@email.com', '555-0102', '456 Maple Ave, Riverside'),
('Mike Davis', 'mike.davis@email.com', '555-0103', '789 Pine Road, Lakewood');

-- Sample notices
INSERT INTO notices (title, message, admin_id) VALUES
('Welcome to PawsHome!', 'We are excited to help you find your perfect furry companion. Browse our available pets and submit an adoption request today!', 1),
('Adoption Event This Weekend', 'Join us this Saturday for our special adoption event. Meet all our available pets and get a chance to take one home!', 1),
('New Pets Available', 'We have just received several new pets looking for loving homes. Check out our latest additions in the Pets section.', 1);
