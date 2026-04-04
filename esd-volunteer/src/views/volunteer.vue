<script>
import EventsCard from '@/components/eventsCard.vue'
import NavBar from '@/components/navBar.vue'
import { useVolunteerStore } from '@/stores/volunteer'

export default {
    components: {
        EventsCard,
        NavBar,
    },

    data() {
        return {
            events: [],
            loading: true,
            error: null,
            volunteer: null,
        }
    },

    computed: {
        volunteerId() {
            const store = useVolunteerStore()
            return store.volunteerId
        },
    },

    mounted() {
        console.log('Store ID:', this.volunteerId)

        if (!this.volunteerId) {
            this.error = 'Volunteer not logged in'
            this.loading = false
            return
        }

        this.fetchVolunteer()
        this.fetchVolunteerEvents()
    },

    methods: {
        async fetchVolunteer() {
            try {
                const response = await fetch(`http://localhost:5002/volunteer/${this.volunteerId}`)
                if (!response.ok) throw new Error('API failed')

                const data = await response.json()
                console.log('Raw API data:', data.data)
                this.volunteer = data.data
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message
            } finally {
                this.loading = false
            }
        },

        async fetchVolunteerEvents() {
            try {
                const response = await fetch(
                    `http://localhost:5012/get_event_by_volunteer/${this.volunteerId}`,
                )
                if (!response.ok) throw new Error('API failed')

                const data = await response.json()
                console.log('Raw API data:', data.data.events)
                this.events = data.data.events
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message
            } finally {
                this.loading = false
            }
        },
    },
}
</script>

<template>
    <main class="h-screen flex flex-col bg-base-100 overflow-hidden">
        <div class="sticky top-0 z-50 border-b border-base-300 bg-base-100/95 backdrop-blur">
            <NavBar />
        </div>

        <div class="flex flex-1 overflow-hidden">
            <aside class="w-80 shrink-0 border-r border-base-300 bg-base-100 p-6">
                <div class="flex h-full flex-col rounded-2xl p-6 shadow-sm border border-base-300">
                    <div
                        class="flex flex-col items-center text-center border-b border-base-300 pb-6"
                    >
                        <div class="avatar placeholder mb-4">
                            <div
                                class="bg-emerald-100 text-emerald-700 rounded-full w-20 h-20 flex items-center justify-center"
                            >
                                <span class="text-2xl font-bold leading-none">
                                    {{ volunteer?.volunteer_name?.charAt(0) || 'V' }}
                                </span>
                            </div>
                        </div>

                        <h2 v-if="volunteer" class="text-2xl font-bold text-base-content">
                            {{ volunteer.volunteer_name }}
                        </h2>
                        <p class="text-sm text-base-content/60 mt-1">Volunteer Profile</p>
                    </div>

                    <div class="mt-6 space-y-5">
                        <div>
                            <p
                                class="text-xs font-semibold uppercase tracking-wide text-base-content/50"
                            >
                                Email
                            </p>
                            <p v-if="volunteer" class="mt-1 text-sm text-base-content">
                                {{ volunteer.email }}
                            </p>
                        </div>

                        <div>
                            <p
                                class="text-xs font-semibold uppercase tracking-wide text-base-content/50"
                            >
                                Contact
                            </p>
                            <p v-if="volunteer" class="mt-1 text-sm text-base-content">
                                {{ volunteer.phone_number }}
                            </p>
                        </div>
                    </div>
                </div>
            </aside>

            <section class="flex-1 min-h-0 overflow-y-auto p-8">
                <div class="mx-auto max-w-7xl">
                    <div class="mb-6 flex items-center justify-between">
                        <div>
                            <h1 class="text-3xl font-bold text-base-content">My Events</h1>
                            <p class="mt-1 text-sm text-base-content/60">
                                View the events you’ve registered for.
                            </p>
                        </div>
                    </div>

                    <div v-if="loading" class="flex h-40 items-center justify-center">
                        <span class="loading loading-spinner loading-lg text-emerald-600"></span>
                    </div>

                    <div v-else-if="error" class="alert alert-error shadow-sm">
                        <span>{{ error }}</span>
                    </div>

                    <div
                        v-else-if="events.length"
                        class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3"
                    >
                        <EventsCard
                            v-for="event in events"
                            :key="event.event_id"
                            :event="event"
                            buttonText="View Event"
                            :eventStatus="event.registration_status"
                            :isRegistered="true"
                        />
                    </div>

                    <div
                        v-else
                        class="flex h-40 items-center justify-center rounded-2xl border border-dashed border-base-300 bg-base-100"
                    >
                        <p class="text-base-content/60">No events found.</p>
                    </div>
                </div>
            </section>
        </div>
    </main>
</template>
