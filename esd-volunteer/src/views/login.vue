<script>
import { useVolunteerStore } from '@/stores/volunteer'
import { useOrganiserStore } from '@/stores/organiser'
import { useSessionStore } from '@/stores/currentRole'
export default {
    name: 'LoginTabs',
    data() {
        return {
            activeTab: 'volunteer',
        }
    },
    methods: {
        async setVolunteer() {
            const sessionStore = useSessionStore()
            sessionStore.setRole('volunteer')
            this.fetchCurrentUser()
        },

        async setOrganiser() {
            const sessionStore = useSessionStore()
            sessionStore.setRole('organiser')
            this.fetchCurrentUser()
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

                <router-link
                @click = "setVolunteer"
                    to="/volunteer"
                    class="btn btn-primary bg-green-600 w-full rounded-xl border-0 text-white"
                >
                    Login as Volunteer
                </router-link>
            </form>

            <form v-else class="space-y-4" @submit.prevent>
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

                <router-link
                @click="setOrganiser"
                    to="/organiser"
                    class="btn btn-primary bg-cyan-700 w-full rounded-xl border-0 text-white"
                >
                    Login as Organiser
                </router-link>
            </form>
        </section>
    </main>
</template>
