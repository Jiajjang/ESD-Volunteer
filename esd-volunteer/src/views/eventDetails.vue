<script setup>
import { useRoute } from 'vue-router'
import { ref, reactive, computed, onMounted } from 'vue'
const route = useRoute()
const eventId = route.params.id  // Gets /event/1 → "1"

// Test data (replace with API fetch)
const events = ref([
  {
    id: 1,
    title: 'Tech Conference 2026',
    description: 'Latest AI and cloud trends from top speakers',
    time: '2026-04-15 09:00',
    location: 'Singapore EXPO',
  },
  {
    id: 2,
    title: 'Vue.js Meetup',
    description: 'Hands-on Vue 3 workshop with live coding',
    time: '2026-04-20 18:30',
    location: 'Google Singapore',

  },
  {
    id: 3,
    title: 'Music Festival',
    description: 'Live bands and food stalls all weekend',
    time: '2026-04-25 14:00',
    location: 'Marina Bay Sands',
  },
])
const event = computed(() => events.value.find(e => e.id == eventId))
</script>

<template>
  <main class="pt-20 p-0 max-w-4xl mx-auto">
    <router-link :to="{ name: 'events'}" class="btn btn-ghost mb-8">
        ← Back to Events
    </ router-link>
    <div v-if="event" class="card bg-base-100  border-2 border-gray px-5 py-5">
      <div class="gap-2 flex flex-col">
        <h1 class="text-4xl font-black">{{ event.title }}</h1>
        <p class="text-lg">{{ event.description}}</p>
      </div>
        <p class="text-lg mt-5">⏰ {{ event.time }}</p>
        <p class="text-lg mt-1">📍 {{ event.location }}</p>
        <button class="w-full mt-6 rounded-lg btn btn-primary py-2">Register</button>
    </div>
    <div v-else class="text-center py-20">
      <h1 class="text-2xl">Event not found</h1>

    </div>
  </main>
</template>