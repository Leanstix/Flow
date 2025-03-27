# Flow - University Social Networking Application

## Overview
Flow is a university-focused social networking application designed to bridge the information gap among Nigerian university students. The platform enables students to engage in academic and social discussions, create and share posts, communicate via messaging and calls, and access advertisements to support young entrepreneurs.

## Features
- **User Registration & Authentication**
  - Simple user registration without email verification
  - Role-based access (students, admins, moderators)

- **Messaging & Communication**
  - Individual and group messaging
  - Audio/video calls (both individual and group)

- **Content Sharing**
  - Post creation and sharing
  - Liking and commenting on posts
  - Advert placement for student entrepreneurs

- **Group Creation & Management**
  - Public and private discussion groups
  - Event and announcement sharing

- **Real-time Notifications**
  - Updates on new messages, likes, comments, and events

## Technologies Used
### **Frontend:**
- **Framework:** Next.js (React-based)
- **Styling:** Tailwind CSS
- **State Management:** Context API / Redux (if needed)
- **WebSockets:** For real-time messaging & calls
- **Hosting:** Vercel

### **Backend:**
- **Framework:** Django (Django Rest Framework)
- **Database:** PostgreSQL
- **Authentication:** Django Auth
- **WebSockets:** Django Channels for real-time communication
- **Hosting:** Render (Free tier, then migrate to paid hosting)

### **Other Tools & Integrations:**
- **GitHub & CI/CD Pipelines** (for version control & deployments)
- **AWS S3** (for media storage - images, profile pictures)
- **Cloudinary** (alternative image hosting)
- **WebRTC** (for audio/video calls)

## Setup & Installation
### **1. Clone the repository**
```sh
   git clone https://github.com/your-username/flow.git
   cd flow
```

### **2. Backend Setup (Django)**
```sh
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # For Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver
```

### **3. Frontend Setup (Next.js)**
```sh
   cd frontend
   npm install
   npm run dev
```

### **4. WebSocket Configuration**
Ensure `Django Channels` is properly configured for WebSockets.

## Deployment
- **Backend:** Hosted on **Render** (initially free, later migrated to dedicated hosting)
- **Frontend:** Hosted on **Vercel**
- **Database:** PostgreSQL (Cloud-based)

## Working Tools Required
- **Laptop or Desktop Computer**
- **Stable Internet Connection** (Monthly Data Subscription Recommended)
- **Access to a Tech Hub or Co-Working Space** (Optional, for better collaboration)
- **Version Control (Git & GitHub)**
- **API Documentation (Swagger API)**

## Roadmap & Future Features
- **AI-powered Post Recommendations**
- **Campus Event Calendar & Reminders**
- **Peer-to-Peer Learning & Tutoring System**
- **Marketplace for Student Entrepreneurs**

## Contribution Guidelines
- Fork the repository
- Create a feature branch (`git checkout -b feature-name`)
- Commit changes (`git commit -m "Feature description"`)
- Push to GitHub (`git push origin feature-name`)
- Submit a pull request for review

## License
This project is licensed under the MIT License.

---
**Developed by Flow Team**

