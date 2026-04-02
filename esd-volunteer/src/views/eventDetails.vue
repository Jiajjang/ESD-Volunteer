<script>
import NavBar from '@/components/navbar.vue'

export default {
    components: {
        NavBar,
    },

    data() {
        return {
            event: null,
            loading: true,
            error: null,
            volunteer_id: 1,
            registeredEvents: [],
            loadingRegistration: true,
            registrationSuccess: false,
            actionLoading: null,
            successMessage: '',
        }
    },

    computed: {
        currentEventId() {
            return this.event?.event_id || this.event?.id || null
        },

        currentRegistration() {
            if (!this.currentEventId) return null

            return this.registeredEvents.find((reg) => reg.event_id === this.currentEventId) || null
        },

        eventStatus() {
            return (
                this.currentRegistration?.registration_status?.trim().toLowerCase() ||
                this.currentRegistration?.status?.trim().toLowerCase() ||
                ''
            )
        },

        statusBadgeClass() {
            if (this.eventStatus === 'confirmed') return 'badge badge-success'
            if (this.eventStatus === 'pending') return 'badge badge-warning'
            return 'badge badge-neutral'
        },

        formattedStatus() {
            if (!this.eventStatus) return ''
            return this.eventStatus.charAt(0).toUpperCase() + this.eventStatus.slice(1)
        },

        isCurrentEventRegistered() {
            return this.eventStatus === 'pending' || this.eventStatus === 'confirmed'
        },

        buttonLabel() {
            if (this.actionLoading === 'register') return 'Registering...'
            if (this.isCurrentEventRegistered) return 'Registered'
            return 'Register'
        },

        buttonClass() {
            if (this.actionLoading === 'register') return 'btn-primary'
            if (this.isCurrentEventRegistered) return 'btn-success'
            return 'btn-primary'
        },
    },

    methods: {
        formatDate(dateString) {
            const date = new Date(dateString)
            return date.toLocaleString('en-SG', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
            })
        },

        async fetchEvent() {
            const response = await fetch(`http://localhost:5001/event/${this.$route.params.id}`)
            if (!response.ok) throw new Error('API failed')

            const data = await response.json()
            this.event = data.data
        },

        async fetchVolunteerEvents() {
            try {
                const response = await fetch(
                    `http://localhost:5012/get_event_by_volunteer/${this.volunteer_id}`,
                )
                if (!response.ok) throw new Error('API failed')

                const data = await response.json()
                this.registeredEvents = data.data.events || []
            } catch (err) {
                this.error = err.message
            } finally {
                this.loadingRegistration = false
            }
        },

        async addRegistration() {
            if (this.isCurrentEventRegistered || !this.currentEventId) return

            this.actionLoading = 'register'
            this.registrationSuccess = false
            this.successMessage = ''

            try {
                const response = await fetch('http://localhost:5010/register_for_event', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        volunteer_id: this.volunteer_id,
                        event_id: this.currentEventId,
                    }),
                })

                if (!response.ok) throw new Error('Registration failed')

                await response.json()
                await this.fetchVolunteerEvents()

                this.successMessage = `Successfully registered for ${this.event.name}!`
                this.registrationSuccess = true

                setTimeout(() => {
                    this.registrationSuccess = false
                    this.successMessage = ''
                }, 3000)
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message
            } finally {
                this.actionLoading = null
            }
        },

        async deleteRegistration() {
            if (!this.isCurrentEventRegistered || !this.currentEventId) return

            this.actionLoading = 'delete'
            this.registrationSuccess = false
            this.successMessage = ''

            try {
                const response = await fetch('http://localhost:5011/cancel-registration', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        volunteer_id: this.volunteer_id,
                        event_id: this.currentEventId,
                    }),
                })

                if (!response.ok) throw new Error('Unregistration failed')

                await response.json()
                await this.fetchVolunteerEvents()

                this.successMessage = `Successfully unregistered from ${this.event.name}!`
                this.registrationSuccess = true

                setTimeout(() => {
                    this.registrationSuccess = false
                    this.successMessage = ''
                }, 3000)
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message
            } finally {
                this.actionLoading = null
            }
        },
    },

    async mounted() {
        try {
            await Promise.all([this.fetchEvent(), this.fetchVolunteerEvents()])
        } catch (err) {
            this.error = err.message
        } finally {
            this.loading = false
        }
    },
}
</script>

<template>
    <NavBar />
    <main class="pt-10 p-0 max-w-3xl mx-auto">
        <router-link :to="{ name: 'events' }" class="btn btn-ghost mb-8">
            ← Back to Events
        </router-link>

        <div v-if="loading">Loading...</div>

        <div v-else-if="event" class="card bg-base-100 border-2 border-gray-300 max-h-130">
            <figure>
                <img src="/cardThumbnail.jpg" class="w-full" />
            </figure>

            <div class="card-body">
                <div class="gap-2 flex flex-row justify-between">
                    <h1 class="text-4xl font-black">{{ event.name }}</h1>

                    <div
                        v-if="eventStatus === 'pending' || eventStatus === 'confirmed'"
                        :class="statusBadgeClass"
                    >
                        {{ formattedStatus }}
                    </div>
                </div>
                <p class="text-lg">{{ event.description }}</p>

                <p class="text-lg mt-5">🕒 {{ formatDate(event.start_date) }}</p>
                <p class="text-lg">📍 {{ event.location }}</p>

                <div class="card-actions justify-end mt-8">
                    <div v-if="registrationSuccess" class="alert alert-success shadow-lg w-full">
                        <span>{{ successMessage }}</span>
                    </div>

                    <button
                        class="w-full rounded-lg btn"
                        :class="buttonClass"
                        :disabled="
                            loadingRegistration ||
                            actionLoading === 'register' ||
                            isCurrentEventRegistered
                        "
                        @click="addRegistration"
                    >
                        {{ buttonLabel }}
                    </button>

                    <button
                        v-if="isCurrentEventRegistered"
                        class="w-full rounded-lg btn btn-error btn-outline py-2"
                        :disabled="loadingRegistration || actionLoading === 'delete'"
                        @click="deleteRegistration"
                    >
                        {{ actionLoading === 'delete' ? 'Unregistering...' : 'Unregister' }}
                    </button>
                </div>
            </div>
        </div>

        <div v-else class="text-center py-20">
            <h1 class="text-2xl">Event not found</h1>
        </div>
    </main>
</template>
