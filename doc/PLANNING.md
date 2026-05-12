# Media Server Plan
### MiniTube


## Questions or Concerns

 *


## Project Goals

 * Domain: Video Streaming

 * Micro-services
    - Commnunication
    - Intelligence

 * Programming languages, Frontend frameworks, and Database
 - Python for backend (FastAPI, to be discussed)
 - React (TypeScript) for frontend (Next.js)
 - Database: RDBMS vs NoSQL???


## Use Cases

### User Accounts and Preferences

1. **Registration (Create account)**
   - User signs up with email, username, password (and any additional data we need)
   - System validates user input (email format, password length, etc.)
   - System checks for duplicate emails/usernames
   - System hashes and stores password

2. **Login**
   - User logs in with their credentials
   - System verifies password, returns session token

3. **Handle invalid login**
   - System returns error for incorrect credentials
   - System does rate limiting after certain number of failed attempts

4. **Reset password**
   - User requests reset
   - System generates temporary password (or some kind of token)
   - User submits new password and temporary password (or token)
   - Temporary password gets expired

5. **Logout**
   - User clicks logout button
   - System redirects to main page (non-logged in version)

6. **View user profile**
   - User clicks on profile button and views their profile

7. **Edit user profile**
   - User updates profile (e.g. new username) via edit/save button
   - System validates user input

8. **Privacy settings**
   - User toggles privacy-related settings (e.g. public/private profiles, etc.)

9. **Notification settings**
   - User configures push notification, chat notification (from real-time chat/messaging)

10. **UI settings**
    - User decides the layout/order of videos being displayed, size of the video screen, etc.

### Admin Dashboard

1. **View system health**
   - Admin clicks on the button to check health
   - System sends a request to /health endpoint
   - Admin sees the result of the reply

2. **View user counts**
   - Admin sees the current real-time user counts
   - Real-time user counts are consistently updated with the calls to some endpoints of REST API
   - Admin sees the updated user counts real-time

3. **View logs**
   - Admin sees the current logs
   - Real-time logs are consistently updated with the calls to some endpoints of REST API
   - Admin sees the updated user logs real-time

4. **Ban user**
   - Admin selects the user to ban them in the UI
   - The patch request is sent to the backend
   - Frontend makes another request to the backend and gets updated

5. **Reset password**
   - Admin can reset their own password
   - The request is sent to the backend
   - Backend sends the email through email service
   - Admin restores the password
   - Password changes in the database
   - Admin can log in now

6. **Delete content**
   - Admin deletes certain video
   - Patch request sent to the database (or wherever we store videos)

7. **View metrics**
   - Admin can go to the metrics window
   - Metrics are updated in real time through sending the get requests to the backend

### Dashboard and Search

1. **Looking for Videos**
   - User logs in
   - The system detects whether the user has any history:
     - If there is, the system generates video recommendations based on trending algorithms and the user's watching history
     - If there is not, the system generates recommendations based solely on trending topics and location-based hotspots
   - User selects a video from the recommendation feed
   - The system retrieves the video metadata and stream URL, adding the new video history to this user's information
   - The system initiates the video player and begins streaming

2. **Search Input**
   - User enters keywords into the search bar on the homepage
   - The system provides real-time search suggestions based on the input
   - The system filters and ranks videos based on relevance, keywords, and user preferences

3. **Subscription list**
   - User views subscription tab, which shows the latest videos from subscribed creators (in chronological order)

4. **Recently watched**
   - User views recently watched videos

5. **Notification tab**
   - User sees notification inbox that contains recent notifications, marked read or unread

6. **Search history**
   - When clicks on the search bar, the system displays a short list of recent search history

7. **Subscribed channel tab**
   - User views a list of channels currently subscribed to
   - User can edit channel-specific settings (unsubscribe, enable/disable notification from the channel, etc.)

8. **Uploaded videos tab**
   - User views a list of uploaded videos by that user

9. **User Profile**
   - When clicks on the Profile section of the Dashboard, the user will be navigated to the Profile page
   - The system retrieves and displays the current profile data (Name, Bio, Avatar…)

### Concurrent CRUD Access

1. **Atomic View Count Update**
   - Multiple users are watching the same viral video simultaneously, which will cause race conditions
   - The system uses an atomic increment (maybe in Redis) and syncs the batch totals asynchronously to the database

2. **Video Metadata Edit**
   - User A changes the Title of the video
   - User B changes the Description of the video seconds later
   - The system uses a version column to update the information of the video

3. **Invalid video metadata during upload**
   - User submits empty title, overly long description, etc.
   - Reject request to upload

4. **Unique email and username**
   - Two users try to use the same email or username
   - System only allows one of the two requests

### Intelligence

1. **AI-summarize**
   - The button to AI-summarize is clicked by user
   - The request is sent to the backend
   - Based on the subtitles the LLM agent is called to summarize the video
   - The summary is returned to the frontend

2. **User can tag their content**
   - The user adds a tag to the content on the frontend
   - The patch request is sent to the backend
   - The database is updated to reflect the tag

3. **User can see the tags**
   - When the user looks at the video
   - The request to backend is sent
   - Backend fetches database and returns tags
   - Tags are displayed with a video

4. **User gets recommended videos based on title and author history**
   - When the dashboard is loaded, Intelligence microservice is called to calculate recommendations
   - Backend determines recommended videos
   - Recommended videos are shown in the user feed

### Communication

1. **New video notification**
   - If there is a new video uploaded to a channel which the user is already subscribed to, system pushes notification
   - System stores notification in an inbox

2. **Notification Inbox**
   - User opens notification tab (or possibly a dashboard) and sees a list of unread notifications
   - System marks as read if user clicks to check the notification

3. **Real-time chat**
   - If multiple users are online, the message is delivered instantly
   - (One real-time chat for each video/trending video/live stream, etc.)

4. **Subscription notification**
   - User subscribes to a new channel
   - System sends a notification to confirm subscription

5. **Chat notification**
   - If there is an active conversation in a previously participated chat, system sends a notification to the user


## Test Scenarios

### User Accounts and Preferences

1. **Check Registration Functionality**
   - Check login functionality
     - Valid login
     - Invalid login
   - Check reset password functionality
   - Check logout functionality
   - Check user profile view functionality
   - Check edit user profile functionality
   - Check privacy settings functionality
     - Check editing
     - Check if privacy settings configure privacy properly
   - Check notification settings functionality
     - Check editing
     - Check if notification settings configure notifications properly
   - Check UI settings
     - Check editing
     - Check if UI settings configure UI properly

### Admin Dashboard

1. **Check if admin can view system health**
2. **Check if admin can view user counts**
3. **Check if admin can view logs**
4. **Check if admin can ban users**
5. **Check if admin can reset their password**
6. **Check if admin can delete content**
7. **Check if admin can view metrics**

### Dashboard and Search

1. **Check if the user dashboard displays the appropriate videos**
2. **Check if you can search the videos**
3. **Check if after search the appropriate videos pop**
4. **Check if you can search through the tags**
5. **Check if user has a subscription list**
6. **Check if a user has recently watched tab with recently watched videos**
7. **Check if user has a notification tab with recent notifications**
8. **Check if user has a search history displayed when they search**

### Concurrent CRUD Access

1. **Check that videos work properly if several people are watching simultaneously**
2. **Check that the video metadata is updated in real time** (author changes the title, user sees it if they refresh the page)

### Intelligence

1. **Check if AI-summarization works properly**
2. **Check if users can tag their content**
3. **Check if users can see the tags**
4. **Check if user gets recommended proper videos**

### Communication

1. **Check that users get new video notifications**
2. **Check that notification inbox is working**
3. **Check that real-time chat is working**
4. **Check that there is a subscription notification**
5. **Check if chat notifications are handled properly**


## APIs

In general, we will strive to have an API for every microservice we have.

### 1. User Accounts and Preferences API

**Purpose:** Handles the full lifecycle of a user, from registration and secure login to personalized UI and privacy settings.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Create account with email, username, and hashed password. |
| POST | /auth/login | Validate credentials and return a session token/JWT. |
| POST | /auth/logout | Invalidate the session and redirect to the landing page. |
| POST | /auth/reset-password | Request a reset token or submit a new password. |
| GET | /user/profile/{id} | Retrieve public profile data (Bio, Avatar, etc.). |
| PATCH | /user/profile/edit | Update username or profile details. |
| PATCH | /user/settings/privacy | Toggle public/private profile visibility. |
| PATCH | /user/settings/notifications | Configure push and chat notification preferences. |
| PATCH | /user/settings/ui | Save custom layout, video size, and display order. |

### 2. Admin Dashboard API

**Purpose:** Provides elevated access for administrators to monitor system health, moderate content, and manage users.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /admin/health | Check the status/health of all running microservices. |
| GET | /admin/users/count | Retrieve real-time count of active and total users. |
| GET | /admin/logs | Fetch real-time system and error logs. |
| PATCH | /admin/users/{id}/ban | Restrict a specific user's access to the platform. |
| POST | /admin/auth/reset | Allow admin to reset their own password via email service. |
| DELETE | /admin/content/{v_id} | Remove a video from storage and the database. |
| GET | /admin/metrics | Retrieve real-time performance and usage metrics. |

### 3. Dashboard and Search API

**Purpose:** Powers the primary user interface, discovery algorithms, and keyword queries.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /dashboard/recommend | Get videos based on history or trending/location hotspots. |
| GET | /search | Filter and rank videos based on keywords and relevance. |
| GET | /search/suggestions | Provide real-time keyword suggestions as the user types. |
| GET | /search/history | Display a list of the user's recent search queries. |
| GET | /subscriptions/feed | List latest videos from subscribed channels (chronological). |
| GET | /user/history/watched | List recently viewed videos for the user. |
| GET | /user/notifications | Fetch recent alerts (read/unread) from the notification inbox. |

### 4. Concurrent CRUD Access API

**Purpose:** Ensures data integrity during high-traffic events, such as viral video view spikes or simultaneous metadata edits.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /crud/check | Validate input constraints (email uniqueness, title length). |
| POST | /crud/add | Handle new video uploads and initial metadata entry. |
| POST | /crud/watch | Atomic view count increment (buffered via Redis). |
| PATCH | /crud/update | Edit video metadata using version-locking to prevent race conditions. |

### 5. Intelligence API

**Purpose:** Leverages LLM agents and recommendation engines to enhance content value and discoverability.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /ai/health | Check the availability of the LLM/Intelligence service. |
| POST | /ai/summarize | Call the LLM agent to summarize a video via its subtitles. |
| POST | /ai/tagging | Add or automatically generate tags for specific content. |
| GET | /ai/tags/{v_id} | Retrieve and display all tags associated with a video. |
| GET | /ai/recommend/logic | Calculate and return recommended videos for the user feed. |

### 6. Communication API

**Purpose:** Manages the real-time social layer, including chat rooms and the notification delivery pipeline.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /comm/notifications | Create and route new video or subscription alerts. |
| PATCH | /comm/notifications/read | Mark a notification as read when clicked by the user. |
| WS | /comm/real-time-chat | Establish a WebSocket connection for instant messaging on videos. |
| POST | /comm/chat/notify | Send a push notification for active chat conversations. |


## User Data Requirements

### User Account Data
Required for authentication; retained until account deletion.

- **Email**
  - Used for login, password recovery, and possibly communication
  - Retained until account deletion

- **Username**
  - Unique identifier shown to other users on the platform
  - Retained until account deletion

- **Password**
  - Used for authentication (login)
  - Never stored in plain text (will be hashed)
  - Retained until account deletion

### Profile & User Preferences Data
Enables personalization; stored until user update or deletion.

- **Profile data**
- **Privacy settings**
- **Notification settings**
- **UI settings**

### User Activity Data

- **Watch history**
  - Tracks videos the user viewed
  - Tracked to generate recommendations
  - Retained until user clears history, or automatically deleted after a certain period of time (e.g. 30 days); users will have control over this

- **Search history**
  - Stores recent search queries, improves search suggestions
  - Retained until user clears history, or automatically deleted after a certain period of time (e.g. 7 days); users will have control over this

### Subscription Data
To enable core features (subscription), we need to keep a list of which channels the user is subscribed to.
- Retained until account deletion

### Communication Data

- **Notifications**
  - Stores user notifications to keep users informed about their account activity
  - Retained for a short period of time (or until user clears notifications)

- **Chat messages**
  - Stores real-time chat messages to allow users to revisit their chat history
  - Retained for a short period of time (or until user clears chat)


## Wireframe

 * [Wireframe (Figma)](https://www.figma.com/make/l4aLrOUNQWQbD8vT53mCOb/Basic-YouTube-Clone?t=VMCbRGpyGuY6JU9O-1)


### Project Starting Priorities

**Core**

1. **User Authentication**
   - Implement basic Registration and Login with password hashing and JWT (to be discussed) management

2. **Basic Video Upload and Storage**
   - Create a simple upload API which can save the video and record the metadata in the database

3. **Video Streaming**
   - Set up a basic video player that can fetch and play the videos from the storage server

4. **Database Schema Design**
   - Initialize the core schema to support basic CRUD operations

**Essential**

5. **Search**
   - Implement a basic search bar with keyword matching and related algorithms

6. **Concurrency Handling**

7. **User Dashboard and Profile**
   - Develop the UI for users to update their profile
   - Users can view their own uploaded videos

**Advanced**

8. **AI Intelligence Integration**
   - Integrate the LLM agent for AI-Summarization and automated tagging

9. **Real-time Communication**
   - Implement WebSockets for real-time chat


### LLM Teammate

 * Name: Bobby

 * Roles: QA (Testing), Dummy Data Generator, Code reviewer (code conventions, quality, suggestions), Suggestion Generator, Documentation Specialist

 * Models: Claude Code, GitHub Copilot
