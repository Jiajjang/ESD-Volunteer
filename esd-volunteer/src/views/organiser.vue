<script>
import EventsCard from '@/components/eventsCard.vue'
import NavBar from '@/components/navBar.vue'
import { useOrganiserStore } from '@/stores/organiser'
import { useSessionStore } from '@/stores/currentRole'

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
            organiser: null,
        }
    },

    computed: {
        organiserName() {
            return this.organiser ? this.organiser.organiser_name : ''
        },
        organiser_id() {
            return useOrganiserStore().organiserId
        },
        eventStatusClass() {
            const status = (this.eventStatus || '').trim().toLowerCase()

            if (status === 'active') return 'badge badge-success'
            if (status === 'cancelled') return 'badge badge-error'
            if (status === 'completed') return 'badge badge-info'
            return 'badge badge-neutral'
        },
        formattedEventStatus() {
            return this.eventStatus
                ? this.eventStatus.charAt(0).toUpperCase() + this.eventStatus.slice(1)
                : 'Unknown'
        },
    },

    methods: {
        async fetchOrganiser() {
            try {
                const response = await fetch(`http://localhost:8000/organiser/${this.organiser_id}`)
                if (!response.ok) throw new Error('Failed to fetch organiser')

                const data = await response.json()
                this.organiser = data.data
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message
            }
        },

        async fetchOrganiserEvents() {
            try {
                const response = await fetch(
                    `http://localhost:8000/event/organiser/${this.organiser_id}`,
                )

                if (response.status === 404) {
                    this.events = []
                    return
                }

                if (!response.ok) throw new Error('Failed to fetch events')

                const data = await response.json()
                this.events = data.data?.events || data.data || []
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message
                this.events = []
            }
        },
    },

    async mounted() {
        const sessionStore = useSessionStore()
        sessionStore.setRole('organiser')

        try {
            await Promise.all([this.fetchOrganiser(), this.fetchOrganiserEvents()])
        } finally {
            this.loading = false
        }
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
                                class="bg-cyan-100 text-cyan-700 rounded-full w-20 h-20 flex items-center justify-center"
                            >
                                <span class="text-2xl font-bold leading-none">
                                    {{ organiser?.organiser_name?.charAt(0) || 'V' }}
                                </span>
                            </div>
                        </div>

                        <h2 v-if="organiser" class="text-2xl font-bold text-base-content">
                            {{ organiser.organiser_name }}
                        </h2>
                        <p class="text-sm text-base-content/60 mt-1">Organiser Profile</p>
                    </div>

                    <div class="mt-6 space-y-5">
                        <div>
                            <p
                                class="text-xs font-semibold uppercase tracking-wide text-base-content/50"
                            >
                                Email
                            </p>
                            <p v-if="organiser" class="mt-1 text-sm text-base-content">
                                {{ organiser.email }}
                            </p>
                        </div>

                        <div>
                            <p
                                class="text-xs font-semibold uppercase tracking-wide text-base-content/50"
                            >
                                Contact
                            </p>
                            <p v-if="organiser" class="mt-1 text-sm text-base-content">
                                {{ organiser.phone_number }}
                            </p>
                        </div>
                        <div>
                            <p
                                class="text-xs font-semibold uppercase tracking-wide text-base-content/50"
                            >
                                Address
                            </p>
                            <p v-if="organiser" class="mt-1 text-sm text-base-content">
                                {{ organiser.registered_address }}
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
                                View the events you’ve created.
                            </p>
                        </div>
                    </div>

                    <div v-if="loading" class="flex h-40 items-center justify-center">
                        <span class="loading loading-spinner loading-lg text-cyan-600"></span>
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
                            :eventStatus="event.status"
                            :eventStatusClass="eventStatusClass"
                            :isRegistered="true"
                        />
                    </div>

                    <div
                        v-else
                        class="flex h-40 items-center justify-center rounded-2xl border border-dashed border-base-300 bg-base-100"
                    >
                        <p class="text-base-content/60">
                            No events found. Create your first event to get started.
                        </p>
                    </div>
                </div>
            </section>
        </div>
    </main>
</template>
