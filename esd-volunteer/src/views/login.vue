<script>
import { useSessionStore } from '@/stores/currentRole'
import { useVolunteerStore } from '@/stores/volunteer'
import { useOrganiserStore } from '@/stores/organiser'

export default {
    name: 'LoginTabs',
    data() {
        return {
            activeTab: 'volunteer',
            volunteerIdInput: null,
            organiserIdInput: null,
        }
    },
    methods: {
        setVolunteer() {
            const sessionStore = useSessionStore()
            const volunteerStore = useVolunteerStore()

            if (volunteerStore.setVolunteerId) {
                volunteerStore.setVolunteerId(Number(this.volunteerIdInput))
            } else {
                volunteerStore.volunteerId = Number(this.volunteerIdInput)
            }

            sessionStore.setRole('volunteer')
            this.$router.push('/volunteer')
        },

        setOrganiser() {
            const sessionStore = useSessionStore()
            const organiserStore = useOrganiserStore()

            if (organiserStore.setOrganiserId) {
                organiserStore.setOrganiserId(Number(this.organiserIdInput))
            } else {
                organiserStore.organiserId = Number(this.organiserIdInput)
            }

            sessionStore.setRole('organiser')
            this.$router.push('/organiser')
        },
    },
}
</script>

<template>
    <main class="min-h-screen grid place-items-center from-blue-50 via-base-100 to-green-50 p-6">
        <section
            class="w-full max-w-md rounded-[28px] border border-white/80 bg-white/90 p-8 shadow-2xl backdrop-blur"
        >
            <p
                :class="activeTab === 'organiser' ? 'text-blue-700' : 'text-green-700'"
                class="mb-2 text-sm font-bold uppercase tracking-[0.18em]"
            >
                {{ activeTab === 'volunteer' ? 'Volunteer portal' : 'Organiser portal' }}
            </p>

            <h1 class="mb-2 text-3xl font-extrabold leading-tight text-base-content">
                {{
                    activeTab === 'volunteer' ? 'Sign in as a volunteer' : 'Sign in as an organiser'
                }}
            </h1>

            <div class="tabs-boxed tabs mb-6 grid w-full grid-cols-2 bg-base-200 p-1.5 rounded-xl">
                <button
                    type="button"
                    class="tab h-12 rounded-xl text-sm font-semibold transition"
                    :class="
                        activeTab === 'volunteer'
                            ? 'tab-active bg-white! text-base-content! shadow'
                            : 'text-base-content/60'
                    "
                    @click="activeTab = 'volunteer'"
                >
                    Volunteer
                </button>
                <button
                    type="button"
                    class="tab h-12 rounded-xl text-sm font-semibold transition"
                    :class="
                        activeTab === 'organiser'
                            ? 'tab-active bg-white! text-base-content! shadow'
                            : 'text-base-content/60'
                    "
                    @click="activeTab = 'organiser'"
                >
                    Organiser
                </button>
            </div>

            <form v-if="activeTab === 'volunteer'" class="space-y-4" @submit.prevent>
                <div class="form-control">
                    <label for="volunteer-id" class="label">
                        <span class="label-text font-semibold text-base-content">Volunteer ID</span>
                    </label>
                    <input
                        id="volunteer-id"
                        v-model.number="volunteerIdInput"
                        type="number"
                        min="1"
                        placeholder="Enter volunteer ID"
                        class="input input-bordered w-full rounded-xl bg-white focus:border-green-600 focus:outline-none"
                    />
                </div>

                <div class="form-control">
                    <label for="vol-email" class="label">
                        <span class="label-text font-semibold text-base-content">Email</span>
                    </label>
                    <input
                        id="vol-email"
                        type="email"
                        placeholder="volunteer@example.com"
                        class="input input-bordered w-full rounded-xl bg-white focus:border-green-600 focus:outline-none"
                    />
                </div>

                <div class="form-control">
                    <label for="vol-password" class="label">
                        <span class="label-text font-semibold text-base-content">Password</span>
                    </label>
                    <input
                        id="vol-password"
                        type="password"
                        placeholder="Enter your password"
                        class="input input-bordered w-full rounded-xl bg-white focus:border-green-600 focus:outline-none"
                    />
                </div>

                <button
                    type="button"
                    @click="setVolunteer"
                    class="btn btn-primary bg-green-600 w-full rounded-xl border-0 text-white"
                >
                    Login as Volunteer
                </button>
            </form>

            <form v-else class="space-y-4" @submit.prevent>
                <div class="form-control">
                    <label for="organiser-id" class="label">
                        <span class="label-text font-semibold text-base-content">Organiser ID</span>
                    </label>
                    <input
                        id="organiser-id"
                        v-model.number="organiserIdInput"
                        type="number"
                        min="1"
                        placeholder="Enter organiser ID"
                        class="input input-bordered w-full rounded-xl bg-white focus:border-blue-600 focus:outline-none"
                    />
                </div>

                <div class="form-control">
                    <label for="org-email" class="label">
                        <span class="label-text font-semibold text-base-content">Email</span>
                    </label>
                    <input
                        id="org-email"
                        type="email"
                        placeholder="organiser@company.com"
                        class="input input-bordered w-full rounded-xl bg-white focus:border-blue-600 focus:outline-none"
                    />
                </div>

                <div class="form-control">
                    <label for="org-password" class="label">
                        <span class="label-text font-semibold text-base-content">Password</span>
                    </label>
                    <input
                        id="org-password"
                        type="password"
                        placeholder="Enter your organiser password"
                        class="input input-bordered w-full rounded-xl bg-white focus:border-blue-600 focus:outline-none"
                    />
                </div>

                <button
                    type="button"
                    @click="setOrganiser"
                    class="btn btn-primary bg-cyan-700 w-full rounded-xl border-0 text-white"
                >
                    Login as Organiser
                </button>
            </form>
        </section>
    </main>
</template>
