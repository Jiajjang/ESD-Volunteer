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
            volunteer: null,
            volunteer_id : 1
        }
    },

    computed: {
        volunteerName() {
            return this.volunteer ? this.volunteer.volunteer_name : ''
        },
    },

    methods: {
        async fetchVolunteer() {
            try {
                const response = await fetch(`http://localhost:5002/volunteer/${this.volunteer_id}`)
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

        async fetchVolunteerEvents(){
            try {
                const response = await fetch(`http://localhost:5012/get_event_by_volunteer/${this.volunteer_id}`)
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
        }
    },

    mounted() {
        this.fetchVolunteer()
        this.fetchVolunteerEvents()
    },
}
</script>

<template>
    <main>
        <NavBar />
        <div class="flex">
            <div class="flex flex-col h-screen bg-gray-100 w-60 shrink-0 p-6">
                <h2 v-if="volunteer" class="text-3xl font-semibold mb-4">
                    {{ volunteer.volunteer_name }}
                </h2>
                <p class="text-lg font-semibold">Email</p>
                <p v-if="volunteer" class="text-base">{{ volunteer.email }}</p>
                <p class="text-lg font-semibold">Contact</p>
                <p v-if="volunteer" class="text-base">{{ volunteer.phone_number }}</p>
            </div>
            <div class="p-10">
                <div v-if="loading">Loading...</div>
                <div v-if="error" class="text-red-500">{{ error }}</div>
                <div v-else-if="events.length" class="grid-cols-3 gap-8 grid">
                    <EventsCard v-for="event in events" :key="event.event_id" :event="event" />
                </div>
            </div>
        </div>
    </main>
</template>