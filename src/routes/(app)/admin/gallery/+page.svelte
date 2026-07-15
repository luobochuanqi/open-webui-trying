<script lang="ts">
	import { onMount } from 'svelte';
	import { getGallery, toggleFeature } from '$lib/apis/images';

	let images: {
		id: string;
		url: string;
		user_name: string;
		filename: string;
		created_at: string;
		featured: boolean;
	}[] = [];
	let loading = true;
	let featuredIds: string[] = [];

	const load = async () => {
		try {
			images = await getGallery(localStorage.token);
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	};

	const handleToggle = async (fileId: string) => {
		try {
			const res = await toggleFeature(localStorage.token, fileId);
			featuredIds = res.featured_ids;
			images = images.map((img) => ({
				...img,
				featured: featuredIds.includes(img.id)
			}));
		} catch (e) {
			console.error(e);
		}
	};

	onMount(load);
</script>

<svelte:head>
	<title>作品管理</title>
</svelte:head>

<div class="p-6">
	<h1 class="text-2xl font-bold mb-6">学生作品管理</h1>

	{#if loading}
		<p class="text-gray-500">加载中...</p>
	{:else if images.length === 0}
		<p class="text-gray-400">暂无生成作品</p>
	{:else}
		<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
			{#each images as img}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
					<img
						src={img.url}
						alt="generated"
						class="w-full h-40 object-cover cursor-pointer"
						loading="lazy"
					/>
					<div class="p-2">
						<p class="text-xs text-gray-500 truncate" title={img.filename}>
							{img.filename}
						</p>
						<p class="text-xs text-gray-400">作者: {img.user_name}</p>
						<button
							class="mt-2 text-xs px-2 py-1 rounded {img.featured ? 'bg-yellow-400 text-black' : 'bg-gray-200 dark:bg-gray-600'}"
							on:click={() => handleToggle(img.id)}
						>
							{img.featured ? '★ 已精选' : '☆ 设为精选'}
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
