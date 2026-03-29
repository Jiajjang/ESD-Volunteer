<script>
import { useRoute } from 'vue-router'
import NavBar from '@/components/navbar.vue'
export default {
    components: {
        NavBar,
    },
    data() {
        return {
            route: null,
            event: null,
            loading: true,
            error: null,
            // Hardcoded volunteer ID for demo purposes
            volunteer_id: 1,
            event_id: null,
        }
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

        test() {
            console.log(this.event_id)
        },

        async fetchEvent() {
            try {
                const response = await fetch(`http://localhost:5001/event/${this.route.params.id}`)
                if (!response.ok) throw new Error('API failed')

                const data = await response.json()
                console.log('Raw API data:', data)

                this.event = data.data
                this.event_id = data.data.event_id
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message
            } finally {
                this.loading = false
            }
        },

        async addRegistration() {
            try {
                const response = await fetch(`http://localhost:5010/register_for_event`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        volunteer_id: this.volunteer_id,
                        event_id: this.event_id,
                    }),
                })
                if (!response.ok) throw new Error('API failed')

                const data = await response.json()
                console.log('Response:', data)
            } catch (err) {
                console.error('API Error:', err)
                this.error = err.message
            } finally {
                this.loading = false
            }
        },
    },

    mounted() {
        this.route = useRoute()
        this.fetchEvent()
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
                <div class="gap-2 flex flex-col">
                    <h1 class="text-4xl font-black">{{ event.name }}</h1>
                    <p class="text-lg">{{ event.description }}</p>
                </div>
                <p class="text-lg mt-5">🕒 {{ formatDate(event.start_date) }}</p>
                <p class="text-lg">📍 {{ event.location }}</p>
                <button
                    class="w-full mt-6 rounded-lg btn btn-primary py-2"
                    v-on:click="addRegistration"
                >
                    Register
                </button>
            </div>
        </div>
        <div v-else class="text-center py-20">
            <h1 class="text-2xl">Event not found</h1>
        </div>
    </main>
</template>
