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
  <main class="pt-20 p-8 max-w-4xl mx-auto">
    <button class="btn btn-ghost mb-8" @click="$router.back()">
      ← Back to Events
    </button>
    <div v-if="event" class="card bg-base-100 shadow-2xl">
      <figure class="px-10 pt-10">
        <img :src="event.photo" alt="Event" class="rounded-xl" />
      </figure>
      <div class="card-body items-center text-center">
        <h1 class="card-title text-4xl">{{ event.title }}</h1>
        <p class="text-lg">{{ event.description }}</p>
        <div class="stats shadow w-full">
          <div class="stat">
            <div class="stat-title">Date & Time</div>
            <div class="stat-value">{{ event.time }}</div>
          </div>
          <div class="stat">
            <div class="stat-title">Location</div>
            <div class="stat-value">{{ event.location }}</div>
          </div>
        </div>
        <div class="card-actions">
          <button class="btn btn-primary btn-lg">Register Now</button>
        </div>
      </div>
    </div>
    <div v-else class="text-center py-20">
      <h1 class="text-2xl">Event not found</h1>
    </div>
  </main>
</template>