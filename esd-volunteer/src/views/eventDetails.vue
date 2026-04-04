<script>
import NavBar from '@/components/navbar.vue'
import { useVolunteerStore } from '@/stores/volunteer'
import { useOrganiserStore } from '@/stores/organiser'
import { useSessionStore } from '@/stores/currentRole'

export default {
    components: {
        NavBar,
    },

    data() {
        return {
            event: null,
            loading: true,
            error: null,
            registeredEvents: [],
            loadingRegistration: true,
            registrationSuccess: false,
            actionLoading: null,
            successMessage: '',
            alertClass: 'alert-success',
        }
    },

    computed: {
        currentEventId() {
            return this.event?.event_id || this.event?.id || null
        },

        currentRegistration() {
            if (!this.currentEventId) return null

            const match = this.registeredEvents.find((reg) => {
                const regEventId = Number(reg.event_id || reg.id)
                const currentId = Number(this.currentEventId)
                const isMatch = regEventId === currentId
                console.log(
                    `Checking reg.event_id ${regEventId} === current ${currentId}:`,
                    isMatch,
                )
                return isMatch
            })

            console.log('Final match:', match)
            return match || null
        },
        eventStatus() {
            return (
                this.currentRegistration?.registration_status?.trim().toLowerCase() ||
                this.currentRegistration?.status?.trim().toLowerCase() ||
                ''
            )
        },

        volunteer_id() {
            return useVolunteerStore().volunteerId
        },

        currentRole() {
            return useSessionStore().currentRole
        },

        currentUserId() {
            return this.currentRole === 'organiser'
                ? useOrganiserStore().organiserId
                : useVolunteerStore().volunteerId
        },

        isVolunteerView() {
            return this.currentRole === 'volunteer'
        },

        isOrganiserView() {
            return this.currentRole === 'organiser'
        },

        statusBadgeClass() {
            if (this.eventStatus === 'confirmed') return 'badge badge-success'
            if (this.eventStatus === 'pending') return 'badge badge-warning'
            if (this.eventStatus === 'waitlisted') return 'badge badge-error'
            return 'badge badge-neutral'
        },

        formattedStatus() {
            if (!this.eventStatus) return ''
            return this.eventStatus.charAt(0).toUpperCase() + this.eventStatus.slice(1)
        },

        isCurrentEventRegistered() {
            return (
                this.eventStatus === 'pending' ||
                this.eventStatus === 'confirmed' ||
                this.eventStatus === 'waitlisted'
            )
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

        // ------------------- FETCH VOL EVENTS TO CHECK STATUS
        async fetchVolunteerEvents() {
            try {
                const response = await fetch(
                    `http://localhost:5012/get_event_by_volunteer/${this.volunteer_id}`,
                )
                if (!response.ok) throw new Error('API failed')

                const data = await response.json()
                const events = data.data.events || []

                console.log('=== RAW API RESPONSE ===')
                console.log('Raw events:', events)
                console.log(
                    'Looking for event_id:',
                    this.currentEventId,
                    typeof this.currentEventId,
                )

                // Log ALL registrations as table
                console.table(
                    events.map((reg) => ({
                        event_id: reg.event_id,
                        registration_id: reg.registration_id || reg.id,
                        status: reg.registration_status || reg.status,
                    })),
                )

                this.registeredEvents = events.filter((reg) => {
                    const status = (reg.registration_status || reg.status || '')
                        .trim()
                        .toLowerCase()
                    return status !== 'cancelled'
                })

                console.log('=== FILTERED registeredEvents ===')
                console.table(
                    this.registeredEvents.map((reg) => ({
                        event_id: reg.event_id,
                        registration_id: reg.registration_id || reg.id,
                        status: reg.registration_status || reg.status,
                    })),
                )

                console.log('currentEventId:', this.currentEventId)
                console.log('MATCHED registration:', this.currentRegistration)
                console.log('registration_id:', this.currentRegistration["registration_id"])
            } catch (err) {
                this.error = err.message
            } finally {
                this.loadingRegistration = false
            }
        },

        // ---------------------- ADD REGISTRATION
        async addRegistration() {
            if (this.isCurrentEventRegistered || !this.currentEventId) return

            this.actionLoading = 'register'
            this.registrationSuccess = false
            this.successMessage = ''
            this.error = null

            try {
                const response = await fetch('http://localhost:5010/register_for_event', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        volunteer_id: this.volunteer_id,
                        event_id: this.currentEventId,
                    }),
                })

                const result = await response.json()
                if (!response.ok) throw new Error(result.message || 'Registration failed')

                const actualStatus = result.data?.status

                if (actualStatus !== 'confirmed' && actualStatus !== 'waitlisted') {
                    throw new Error(`Unexpected registration status: ${actualStatus}`)
                }

                await this.fetchVolunteerEvents()

                if (actualStatus === 'waitlisted') {
                    this.successMessage = "Event full, you've been added to the waitlist"
                    this.alertClass = 'alert-warning'
                } else {
                    this.successMessage = `Successfully registered for ${this.event.name}!`
                    this.alertClass = 'alert-success'
                }

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
        // ---------------- DELETE REGISTRATION
        async deleteRegistration() {
            console.log(this.currentRegistrationId)
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
                        registration_id: this.currentRegistration["registration_id"],
                    }),
                })

                if (!response.ok) throw new Error('Unregistration failed')
                console.log('delete payload', {
                    volunteer_id: this.volunteer_id,
                    event_id: this.currentEventId,
                    registration_id: this.currentRegistrationId,
                    currentRegistration: this.currentRegistration,
                    registeredEvents: this.registeredEvents,
                })
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
            // Fetch event FIRST, then volunteer events
            await this.fetchEvent()
            await this.fetchVolunteerEvents()
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
    <main class="pt-8 p-0 max-w-3xl mx-auto">
        <button @click="$router.back()" class="btn btn-ghost mb-8">← Back</button>

        <div v-if="loading">Loading...</div>

        <div v-else-if="event" class="card bg-base-100 border-2 border-gray-300 max-h-130">
            <figure>
                <img src="/cardThumbnail.jpg" class="w-full" />
            </figure>

            <div class="card-body">
                <div class="gap-2 flex flex-row justify-between items-center">
                    <h1 class="text-4xl font-black">{{ event.name }}</h1>

                    <div
                        v-if="
                            isVolunteerView &&
                            (eventStatus === 'pending' ||
                                eventStatus === 'confirmed' ||
                                eventStatus === 'waitlisted')
                        "
                        :class="statusBadgeClass"
                    >
                        {{ formattedStatus }}
                    </div>
                </div>

                <p class="text-lg">{{ event.description }}</p>

                <p class="text-lg mt-5">🕒 {{ formatDate(event.start_date) }}</p>
                <p class="text-lg">📍 {{ event.location }}</p>

                <div class="card-actions justify-end mt-8">
                    <div
                        v-if="registrationSuccess"
                        :class="['alert', alertClass, 'shadow-lg', 'w-full']"
                    >
                        <span>{{ successMessage }}</span>
                    </div>

                    <!-- Volunteer actions -->
                    <template v-if="isVolunteerView">
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
                            v-if="isCurrentEventRegistered && eventStatus !== 'waitlisted'"
                            class="w-full rounded-lg btn btn-error btn-outline py-2"
                            :disabled="loadingRegistration || actionLoading === 'delete'"
                            @click="deleteRegistration"
                        >
                            {{ actionLoading === 'delete' ? 'Unregistering...' : 'Unregister' }}
                        </button>
                    </template>

                    <!-- Organiser actions -->
                    <template v-else>
                        <div class="flex flex-row flex-wrap w-full gap-4">
                            <button
                                class="w-full rounded-lg btn btn-outline btn-info flex-1/3 grow"
                                @click="editEvent"
                            >
                                Edit Event
                            </button>
                            <button
                                class="w-full rounded-lg btn btn-outline flex-1/3 grow"
                                @click="viewRegistrations"
                            >
                                View Registrations
                            </button>
                            <button
                                class="w-full rounded-lg btn btn-error btn-outline"
                                @click="deleteEvent"
                            >
                                Delete Event
                            </button>
                        </div>
                    </template>
                </div>
            </div>
        </div>

        <div v-else class="text-center py-20">
            <h1 class="text-2xl">Event not found</h1>
        </div>
    </main>
</template>
