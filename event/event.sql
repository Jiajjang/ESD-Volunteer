CREATE TABLE event (
    event_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    organiser_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    max_capacity INT NOT NULL,
    current_capacity INT DEFAULT 0,
    location TEXT,
    reason TEXT
);