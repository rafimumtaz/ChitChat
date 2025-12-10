# Setup Instructions

This guide provides step-by-step instructions to set up and run the Distributed Chat Application.

## Prerequisites

Ensure you have the following installed on your machine:
- **Python 3.8+**
- **Node.js 16+** & **npm**
- **MySQL Server**
- **RabbitMQ Server**

---

## 1. Database Setup

1. Start your MySQL Server.
2. Create the database and tables by importing the SQL file:
   ```bash
   mysql -u root -p < chat_distributed_db.sql
   ```
   *Note: This will create a database named `chat_distributed_db` (if configured in the SQL or manually created).*

   If the SQL file does not contain `CREATE DATABASE`, create it first:
   ```sql
   CREATE DATABASE chat_distributed_db;
   USE chat_distributed_db;
   SOURCE chat_distributed_db.sql;
   ```

---

## 2. Backend Setup (Flask & RabbitMQ)

The backend consists of a Publisher (API), a Consumer (Worker), and a Broker Setup script.

### a. Install Dependencies
Navigate to the root directory and install the required Python packages:
```bash
pip install -r requirements.txt
```

### b. Environment Variables (.env)
Create a `.env` file in the root directory (or ensure the environment variables are set) for the backend.
**Recommended `.env` content:**

```ini
# Database Configuration
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASS=your_password
DB_NAME=chat_distributed_db
DB_POOL_SIZE=5

# RabbitMQ Configuration
RABBITMQ_HOST=localhost
```

### c. Initialize RabbitMQ
Run the broker setup script once to create the necessary Exchange and Queue:
```bash
python chat-distributed/broker/rabbitmq_broker.py
```
*This ensures the `chat_exchange` and `chat_queue` are created and bound correctly.*

### d. Run the Services
You need to run the Publisher and Consumer in separate terminal windows.

**Terminal 1: Publisher (Auth API & Message Sender)**
```bash
python chat-distributed/publisher/message_publisher.py
```
*Server will start at `http://localhost:5000`.*

**Terminal 2: Consumer (Message Worker)**
```bash
python chat-distributed/consumer/Message_Consumer.py
```
*This worker listens for messages from RabbitMQ and saves them to the database.*

---

## 3. Frontend Setup (Next.js)

### a. Install Dependencies
Navigate to the root directory (where `package.json` is) and install dependencies:
```bash
npm install
```

### b. Environment Variables (.env.local)
Create a `.env.local` file in the root directory to configure the API URL.

**`.env.local` content:**
```ini
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### c. Run the Development Server
```bash
npm run dev
```
*The application will be available at `http://localhost:3000`.*

---

## 4. Verification

1. Open your browser and go to `http://localhost:3000/register`.
2. Create a new account.
3. Login at `http://localhost:3000/login`.
4. Create a new chatroom using the '+' icon in the sidebar.
5. (Optional) Use Postman or Curl to test sending a message to `http://localhost:5000/send-message` and verify it appears in the MySQL `messages` table.
