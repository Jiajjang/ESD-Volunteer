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
        }
    },

    methods: {
        async fetchEvents() {
            try {
                const response = await fetch('http://localhost:5001/event')
                if (!response.ok) throw new Error('API failed')

                const data = await response.json()
                console.log('Raw API data:', data.data)

                this.events = data.data
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message
            } finally {
                this.loading = false
            }
        },
    },

    mounted() {
        this.fetchEvents()
    },
}
</script>

<template>
    <NavBar />
    <main class="px-18 pb-8">
        <h1 class="text-4xl py-8 font-bold">Events</h1>
        <div v-if="loading">Loading...</div>
        <div v-if="error" class="text-red-500">{{ error }}</div>
        <div v-else="events.length" class="grid-cols-3 gap-8 grid">
            <EventsCard v-for="event in events" :key="event.id" :event="event" />
        </div>
    </main>
</template>
