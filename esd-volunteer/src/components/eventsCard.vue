<script>
export default {
  name: 'eventsCard',
  props: {
    event: {
      type: Object,
      required: true,
    },
  },
}
</script>

<template>
  <div class="card w-full shadow-xl hover:shadow-2xl transition-shadow">
    <div class="card-body">
      <h2 class="card-title">{{ event.title }}</h2>
      <p>{{ event.description }}</p>
      <div class="text-sm opacity-75 mb-4">
        <p>
          <strong>🕒 {{ event.time }}</strong>
        </p>
        <p>
          <strong>📍 {{ event.location }}</strong>
        </p>
      </div>
      <div class="card-actions justify-end">
        <router-link :to="{ name: 'eventDetails', params: { id: event.id } }" class="btn btn-primary w-full">
            Register
        </ router-link>
      </div>
    </div>
  </div>
</template>
