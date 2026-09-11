<script setup>
/** 校徽风 Logo：金环双圈 + 菱形星点 + 衬线 C + CITYU 字样 */
defineProps({
  /** 小尺寸(头像等)用：隐藏星点与底部字样，仅双环+大 C */
  simple: { type: Boolean, default: false },
})
</script>

<template>
  <svg class="logo-mark" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <radialGradient id="logo-bg" cx="35%" cy="28%" r="85%">
        <stop offset="0%" stop-color="#136b5b" />
        <stop offset="100%" stop-color="#06281f" />
      </radialGradient>
    </defs>
    <!-- 底与外金环 -->
    <circle cx="32" cy="32" r="31" fill="url(#logo-bg)" />
    <circle cx="32" cy="32" r="30" fill="none" stroke="#c8a565" stroke-width="1.7" />
    <!-- 内细环 -->
    <circle cx="32" cy="32" r="24.5" fill="none" stroke="#c8a565" stroke-width="0.7" opacity="0.55" />
    <template v-if="!simple">
      <!-- 顶部菱形星点 -->
      <rect x="29.9" y="7.9" width="4.2" height="4.2" transform="rotate(45 32 10)" fill="#c8a565" />
      <!-- 底部字样 -->
      <text
        x="32" y="51.5" text-anchor="middle"
        font-family="Georgia, 'Times New Roman', serif"
        font-size="4.6" fill="#c8a565" opacity="0.78" letter-spacing="1.6"
      >CITYU</text>
      <text
        x="32" y="42" text-anchor="middle"
        font-family="Georgia, 'Times New Roman', serif"
        font-size="26" font-weight="600" fill="#c8a565"
      >C</text>
    </template>
    <text
      v-else x="32" y="43" text-anchor="middle"
      font-family="Georgia, 'Times New Roman', serif"
      font-size="28" font-weight="600" fill="#c8a565"
    >C</text>
  </svg>
</template>

<style scoped>
.logo-mark {
  width: 100%;
  height: 100%;
  display: block;
  filter: drop-shadow(0 2px 6px rgba(6, 40, 31, 0.25));
}
</style>
