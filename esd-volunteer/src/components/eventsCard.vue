<script>
export default {
    name: 'eventsCard',
    props: {
        event: {
            type: Object,
            required: true,
        },
        buttonText: {
            type: String,
            default: 'Register',
        },
        isRegistered: {
            type: Boolean,
            default: false,
        },
        eventStatus: {
            type: String,
            default: '',
        },
    },
    computed: {
        statusBadgeClass() {
            if (this.eventStatus === 'confirmed') return 'badge badge-success'
            if (this.eventStatus === 'pending') return 'badge badge-warning'
            if (this.eventStatus === 'waitlisted') return 'badge badge-error'
            return 'badge badge-neutral'
        },
        formattedStatus() {
            if (!this.eventStatus) return ''
            return this.eventStatus.charAt(0).toUpperCase() + this.eventStatus.slice(1)
        },
        displayButtonText() {
            return this.isRegistered ? 'View Event' : this.buttonText
        },
        isEventCancelled() {
            return (this.event?.status || '').trim().toLowerCase() === 'cancelled'
        },
        displayButtonText() {
            if (this.isEventCancelled) return 'Event Cancelled'
            return this.isRegistered ? 'View Event' : this.buttonText
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
    <div class="card h-full w-full shadow-xl hover:shadow-2xl transition-shadow">
        <figure>
            <img src="/cardThumbnail.jpg" class="w-full h-40 object-cover" />
        </figure>

        <div class="card-body flex flex-col h-80">
            <div class="flex items-start justify-between gap-3">
                <h2 class="card-title text-xl flex-1">{{ event.name }}</h2>

                <div
                    v-if="
                        eventStatus &&
                        (eventStatus === 'pending' ||
                            eventStatus === 'confirmed' ||
                            eventStatus === 'waitlisted')
                    "
                    :class="statusBadgeClass"
                >
                    {{ formattedStatus }}
                </div>
            </div>

            <p class="text-base line-clamp-3 min-h-">
                {{ event.description }}
            </p>

            <div class="text-sm opacity-75 mb-4 flex flex-col gap-1 mt-2">
                <p class="text-black text-base">🕒 {{ formatDate(event.start_date) }}</p>
                <p class="text-black text-base">📍 {{ event.location }}</p>
            </div>

            <div class="card-actions justify-end mt-auto">
                <button v-if="isEventCancelled" class="btn w-full btn-disabled" disabled>
                    {{ displayButtonText }}
                </button>

                <router-link
                    v-else
                    :to="{ name: 'eventDetails', params: { id: event.event_id } }"
                    class="btn w-full"
                    :class="isRegistered ? 'btn-outline btn-secondary' : 'btn-primary'"
                >
                    {{ displayButtonText }}
                </router-link>
            </div>
        </div>
    </div>
</template>
