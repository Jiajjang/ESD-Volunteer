<script>
import NavBar from '@/components/navBar.vue'
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
            deleteReason: '',
            promotionLoading: false,
            promotionAction: null,
            promotionError: null,
            promotionSuccess: '',
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
            return match || null
        },

        registrationState() {
            const status =
                this.currentRegistration?.registration_status?.trim().toLowerCase() ||
                this.currentRegistration?.status?.trim().toLowerCase() ||
                ''
            return status || null
        },

        currentRegistrationId() {
            return this.currentRegistration?.registration_id || null
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

        formattedStatus() {
            if (!this.registrationState) return ''
            return this.registrationState.charAt(0).toUpperCase() + this.registrationState.slice(1)
        },

        statusBadgeClass() {
            if (this.registrationState === 'confirmed') return 'badge badge-success'
            if (this.registrationState === 'pending') return 'badge badge-warning'
            if (this.registrationState === 'waitlisted') return 'badge badge-error'
            return 'badge badge-neutral'
        },

        isCurrentEventRegistered() {
            return !!this.registrationState // Truthy = registered
        },

        buttonLabel() {
            if (this.actionLoading === 'register') return 'Registering...'
            if (this.registrationState) return 'Registered'
            return 'Register'
        },

        buttonClass() {
            if (this.actionLoading === 'register') return 'btn-primary'
            if (this.registrationState) return 'btn-success'
            return 'btn-primary'
        },

        isEventCancelled() {
            const status = (this.event?.status || '').trim().toLowerCase()
            return status === 'cancelled'
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
            const response = await fetch(`http://localhost:8000/event/${this.$route.params.id}`)
            if (!response.ok) throw new Error('API failed')
            const data = await response.json()
            this.event = data.data
        },

        // ------------------- FETCH VOL EVENTS TO CHECK STATUS
        async fetchVolunteerEvents() {
            try {
                const response = await fetch(
                    `http://localhost:8000/get_event_by_volunteer/${this.volunteer_id}`,
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

                this.registeredEvents = events.filter((reg) => {
                    const status = (reg.registration_status || reg.status || '')
                        .trim()
                        .toLowerCase()
                    return status !== 'cancelled'
                })

                console.log('currentEventId:', this.currentEventId)
                console.log('MATCHED registration:', this.currentRegistration)
                console.log('registration_id:', this.currentRegistration['registration_id'])
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
                const response = await fetch('http://localhost:8000/register_for_event', {
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
        // ----------------VOLUNTEER CANCEL REGISTRATION
        async deleteRegistration() {
            if (!this.isCurrentEventRegistered || !this.currentEventId) return

            this.actionLoading = 'delete'
            this.registrationSuccess = false
            this.successMessage = ''
            try {
                const response = await fetch('http://localhost:8000/cancel-registration', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        volunteer_id: this.volunteer_id,
                        event_id: this.currentEventId,
                        registration_id: this.currentRegistration['registration_id'],
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
        // --------- ORGANISER DELETE EVENT
        openDeleteModal() {
            this.deleteReason = ''
            this.$refs.deleteModal?.showModal()
        },

        async deleteEvent() {
            if (!this.currentEventId) return
            if (!this.deleteReason?.trim()) {
                this.error = 'Please provide a reason'
                return
            }

            this.actionLoading = 'delete'
            this.registrationSuccess = false
            this.successMessage = ''
            this.error = null

            try {
                const response = await fetch(
                    `http://localhost:8000/event/delete/${this.currentEventId}`,
                    {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            reason: this.deleteReason.trim(),
                        }),
                    },
                )

                const contentType = response.headers.get('content-type') || ''
                const result = contentType.includes('application/json')
                    ? await response.json()
                    : await response.text()

                if (!response.ok) {
                    const message =
                        result?.message ||
                        result?.error ||
                        (typeof result === 'string'
                            ? result
                            : `Delete failed with status ${response.status}`)
                    throw new Error(message)
                }

                console.log('delete success', {
                    event_id: this.currentEventId,
                    result,
                })

                this.event.status = 'cancelled'
                this.successMessage = `Successfully cancelled ${this.event.name}!`
                this.registrationSuccess = true

                this.deleteReason = ''
                this.$refs.deleteModal?.close()

                setTimeout(() => {
                    this.registrationSuccess = false
                    this.successMessage = ''
                }, 3000)

                this.$router.push('/organiser')
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message || 'Failed to cancel event'
            } finally {
                this.actionLoading = null
            }
        },
        // --------------- Waitlist
        async respondToPromotion(volunteerId, eventId, status) {
    if (!volunteerId || !eventId || !['confirmed', 'rejected'].includes(status)) {
        this.error = 'Invalid promotion parameters'
        return
    }

    try {
        this.actionLoading = `promotion-${status}`
        const response = await fetch(
            `http://localhost:8000/cancel-registration/respond`,
            {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ volunteer_id: volunteerId, event_id: eventId, status }),
            }
        )
        const data = await response.json()
        if (!response.ok) throw new Error(data.message || 'Failed to respond')

        // Update local registration state
        const reg = this.registeredEvents.find(r => r.volunteer_id === volunteerId)
        if (reg) reg.registration_status = status

        // Show success message
        this.successMessage = `Volunteer ${status === 'confirmed' ? 'accepted' : 'rejected'} successfully`
        this.alertClass = status === 'confirmed' ? 'alert-success' : 'alert-error'
        this.registrationSuccess = true
        setTimeout(() => {
            this.registrationSuccess = false
            this.successMessage = ''
        }, 3000)

    } catch (err) {
        console.error('Respond to promotion error:', err)
        this.error = err.message || 'Network error'
    } finally {
        this.actionLoading = null
    }
}
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
                            (registrationState === 'pending' ||
                                registrationState === 'confirmed' ||
                                registrationState === 'waitlisted')
                        "
                        class="badge"
                        :class="{
                            'badge-success': registrationState === 'confirmed',
                            'badge-warning': registrationState === 'pending',
                            'badge-error': registrationState === 'waitlisted',
                            'badge-neutral': !registrationState,
                        }"
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
                        <div
                            v-if="registrationState === 'pending'"
                            class="flex flex-row gap-2 w-full"
                        >
                            <button
                                class="btn btn-primary flex-1"
                                :disabled="promotionLoading"
                                @click="
                                    respondToPromotion(volunteer_id, currentEventId, 'confirmed')
                                "
                            >
                                {{
                                    promotionLoading && promotionAction === 'confirmed'
                                        ? 'Accepting...'
                                        : 'Accept Registration'
                                }}
                            </button>

                            <button
                                class="btn btn-outline btn-accent flex-1"
                                :disabled="promotionLoading"
                                @click="
                                    respondToPromotion(volunteer_id, currentEventId, 'rejected')
                                "
                            >
                                {{
                                    promotionLoading && promotionAction === 'rejected'
                                        ? 'Rejecting...'
                                        : 'Reject Registration'
                                }}
                            </button>
                        </div>
                        <div
                            class="flex flex-col w-full gap-2"
                            v-else-if="
                                isCurrentEventRegistered && registrationState === 'confirmed'
                            "
                        >
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
                                class="w-full rounded-lg btn btn-error btn-outline py-2"
                                :disabled="loadingRegistration || actionLoading === 'delete'"
                                @click="deleteRegistration"
                            >
                                {{ actionLoading === 'delete' ? 'Unregistering...' : 'Unregister' }}
                            </button>
                        </div>
                    </template>

                    <!-- Organiser actions -->
                    <template v-else>
                        <button
                            v-if="isEventCancelled"
                            class="w-full rounded-lg btn btn-neutral"
                            disabled
                        >
                            Event Cancelled
                        </button>

                        <div v-else class="flex flex-row flex-wrap w-full gap-4">
                            <button
                                class="w-full rounded-lg btn btn-outline btn-info flex-1/3 grow"
                            >
                                Edit Event
                            </button>

                            <button class="w-full rounded-lg btn btn-outline flex-1/3 grow">
                                View Registrations
                            </button>

                            <button
                                class="w-full rounded-lg btn btn-error btn-outline"
                                :disabled="actionLoading === 'delete'"
                                @click="openDeleteModal"
                            >
                                Delete Event
                            </button>
                        </div>

                        <dialog ref="deleteModal" class="modal">
                            <div class="modal-box">
                                <h3 class="text-lg font-bold">Delete event?</h3>
                                <p class="py-2 text-sm text-base-content/70">
                                    Please provide a reason before deleting this event.
                                </p>

                                <div class="form-control w-full">
                                    <textarea
                                        v-model="deleteReason"
                                        class="textarea textarea-bordered w-full"
                                        placeholder="Enter reason for deleting this event"
                                        rows="4"
                                    ></textarea>
                                </div>

                                <div class="modal-action">
                                    <form method="dialog">
                                        <button class="btn">Close</button>
                                    </form>

                                    <button
                                        class="btn btn-error"
                                        :disabled="
                                            actionLoading === 'delete' || !deleteReason.trim()
                                        "
                                        @click="deleteEvent"
                                    >
                                        {{
                                            actionLoading === 'delete'
                                                ? 'Cancelling Event...'
                                                : 'Delete Event'
                                        }}
                                    </button>
                                </div>
                            </div>

                            <form method="dialog" class="modal-backdrop">
                                <button>close</button>
                            </form>
                        </dialog>
                    </template>
                </div>
            </div>
        </div>

        <div v-else class="text-center py-20">
            <h1 class="text-2xl">Event not found</h1>
        </div>
    </main>
</template>
