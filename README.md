# ESD Volunteer

![Python](https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white)
![Vue](https://img.shields.io/badge/vue-3.x-42b883?logo=vue.js&logoColor=white)
![Docker Compose](https://img.shields.io/badge/build-docker_compose-2496ED?logo=docker&logoColor=white)
![Gateway](https://img.shields.io/badge/gateway-kong%203.9-003459)

ESD Volunteer is a microservices-based event registration platform for volunteer programs. It includes:

- A Vue 3 frontend for volunteers and organisers
- Python Flask services for event, volunteer, organiser, registration, and waitlist domains
- Composite services for cross-service workflows (register, cancel, and volunteer event view)
- Kong API Gateway for unified routing
- RabbitMQ for asynchronous event-driven notifications and cancellations

## Architecture At A Glance

### Core Services
- `registration` (port `5000`): registration lifecycle and status updates
- `event` (port `5001`): event CRUD-like retrieval, capacity updates, event cancellation publish
- `volunteer` (port `5002`): volunteer profile and account management
- `waitlist` (port `5003`): queue operations and cancellation-driven queue cleanup
- `organiser` (port `5004`): organiser profile and account management

### Composite Services
- `register_for_event` (port `5010`): confirms or waitlists a volunteer
- `delete_registration` (port `5011`): cancel flow, promotion to pending, timeout handling
- `get_event_by_volunteer` (port `5012`): aggregate volunteer registrations with event details

### Infrastructure
- Kong Gateway (`8000` proxy): routes external traffic to services
- RabbitMQ (Cloud AMQP): asynchronous messaging
- Frontend (`8080`): production-built Vue app served statically

## Project Structure

```text
.
├─ compose.yaml
├─ kong.yml
├─ esd-volunteer/               # Vue frontend (Vite)
├─ event/                       # Event atomic service
├─ registration/                # Registration atomic service + consumer
├─ volunteer/                   # Volunteer atomic service
├─ organiser/                   # Organiser atomic service
├─ waitlist/                    # Waitlist atomic service
├─ register_for_event/          # Composite service (register flow)
├─ delete_registration/         # Composite service (cancel/respond/timeout)
└─ get_event_by_volunteer/      # Composite service (event list by volunteer)
```

## Getting Started
### Prerequisites
- Docker + Docker Compose
- Node.js 20+ (for local frontend development outside Docker)
- Python 3.10+ (for local service development outside Docker)
- Supabase project and credentials

### 1. Configure Environment Variables
Create a root `.env` file (same folder as `compose.yaml`) with at least:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

RABBITMQ_HOST=your_rabbitmq_host
RABBITMQ_PORT=5672
RABBITMQ_VHOST=your_rabbitmq_vhost
RABBITMQ_USER=your_rabbitmq_user
RABBITMQ_PASS=your_rabbitmq_password
```

### 2. Start Everything (Recommended)

```bash
docker compose up --build
```
### API Routes Overview
- `/event`, `/event/:event_id`, `/event/:event_id/capacity`, `/event/delete/:event_id`
- `/registration`, `/registration/:event_id`, `/registration/volunteer/:volunteer_id`, `/registration/status`
- `/volunteer`, `/volunteer/:volunteer_id`
- `/organiser`, `/organiser/:organiserID`
- `/waitlist/:event_id`, `/waitlist/:event_id/next`
- `/register_for_event`
- `/cancel-registration`, `/cancel-registration/respond`, `/cancel-registration/timeout`
- `/get_event_by_volunteer/:volunteer_id`