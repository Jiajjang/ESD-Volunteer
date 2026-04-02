<script>
import EventsCard from '@/components/eventsCard.vue'
import NavBar from '@/components/navbar.vue'

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
            registeredEvents: [],
            volunteer_id: 1,
        }
    },
    computed: {
        eventsWithRegistration() {
            return this.events.map((event) => {
                const registeredEvent = this.registeredEvents.find(
                    (reg) => reg.event_id === event.event_id,
                )

                return {
                    ...event,
                    registrationStatus: registeredEvent ? registeredEvent.registration_status : '',
                    isRegistered: !!registeredEvent,
                }
            })
        },
    },

    methods: {
        async fetchEvents() {
            const response = await fetch('http://localhost:5001/event')
            if (!response.ok) throw new Error('API failed')

            const data = await response.json()
            this.events = data.data
            this.events.filter(event => 
            event.status !== 'cancelled')
        },

        async fetchVolunteerEvents() {
            const response = await fetch(
                `http://localhost:5012/get_event_by_volunteer/${this.volunteer_id}`,
            )
            if (!response.ok) throw new Error('API failed')

            const data = await response.json()
            this.registeredEvents = data.data.events
        },
    },

    async mounted() {
        try {
            await Promise.all([this.fetchEvents(), this.fetchVolunteerEvents()])
        } catch (err) {
            console.error('API Error:', err)
            this.error = err.message
        } finally {
            this.loading = false
        }
        console.log(this.eventsWithRegistration)
        console.log(this.registration)
    },
}
</script>

<template>
    <NavBar />
    <main class="px-18 pb-8">
        <h1 class="text-4xl py-8 font-bold">Events</h1>

        <div v-if="loading">Loading...</div>

        <div v-else-if="error" class="text-red-500">{{ error }}</div>

        <div v-else-if="eventsWithRegistration.length" class="grid grid-cols-3 gap-8">
            <EventsCard
                v-for="event in eventsWithRegistration"
                :key="event.event_id"
                :event="event"
                :buttonText="event.isRegistered ? 'View Event' : 'Register'"
                :eventStatus="event.registrationStatus"
                :isRegistered="event.isRegistered"
            />
        </div>

        <div v-else>No events found.</div>
    </main>
</template>
