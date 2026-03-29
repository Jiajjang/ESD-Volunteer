<script>
export default {
	name: 'eventsCard',
	props: {
		event: {
			type: Object,
			required: true,
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
	},
}
</script>

<template>
	<div class="card w-full shadow-xl hover:shadow-2xl transition-shadow max-h-105">
		<figure>
			<img src="/cardThumbnail.jpg" class="w-full" />
		</figure>
		<div class="card-body">
			<h2 class="card-title text-xl">{{ event.name }}</h2>
			<p class="text-base">{{ event.description }}</p>
			<div class="text-sm opacity-75 mb-4 flex flex-col gap-1 mt-2">
				<p class="text-black text-base">🕒 {{ formatDate(event.start_date) }}</p>
				<p class="text-black text-base">📍 {{ event.location }}</p>
			</div>
			<div class="card-actions justify-end">
				<router-link
					:to="{ name: 'eventDetails', params: { id: event.event_id } }"
					class="btn btn-primary w-full"
				>
					Register
				</router-link>
			</div>
		</div>
	</div>
</template>
