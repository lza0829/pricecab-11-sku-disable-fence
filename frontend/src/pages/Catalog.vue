<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const skus = ref([])
const policy = ref(null)
const msg = ref('')
const warn = ref('')
const err = ref('')
const busy = ref('')

async function refresh() {
  skus.value = await api.skus()
  policy.value = await api.policy()
}

async function toggle(sku) {
  msg.value = ''
  err.value = ''
  warn.value = ''
  busy.value = sku.sku_code
  try {
    const next = !sku.enabled
    const res = await api.setSkuEnabled(sku.sku_code, next)
    msg.value = `${sku.sku_code} 已${next ? '启用' : '停用'}`
    if (!next && res.scheduled_tickets && res.scheduled_tickets.length) {
      warn.value = `注意：${res.scheduled_tickets.join('、')} 仍含该商品，`
        + (policy.value && policy.value.disabled_sku_policy === 'skip_on_apply'
          ? '应用时将跳过该行并计数，不写其价签。'
          : '应用时将整单拒绝，不会写入任何价签。')
    }
    await refresh()
  } catch (e) {
    err.value = e.message
  } finally {
    busy.value = ''
  }
}

onMounted(() => refresh().catch((e) => (err.value = e.message)))
</script>

<template>
  <section class="hero">
    <h1>商品启停</h1>
    <p>停用商品不再允许进入新的改价明细，且应用时绝不会改写其价签。</p>
  </section>

  <div v-if="policy" class="panel policy">
    <h2>停用策略（全局唯一）</h2>
    <p>
      <span class="tag warn">{{ policy.disabled_sku_policy_label }}</span>
      <code>{{ policy.disabled_sku_policy }}</code>
    </p>
    <p class="msg">{{ policy.disabled_sku_policy_summary }}</p>
    <p class="msg">本部署只贯彻这一种策略，改价单建单与应用始终一致。</p>
  </div>

  <p v-if="msg" class="msg ok">{{ msg }}</p>
  <p v-if="warn" class="msg warn-text">{{ warn }}</p>
  <p v-if="err" class="msg err">{{ err }}</p>

  <div class="panel">
    <h2>商品</h2>
    <table>
      <thead>
        <tr><th>SKU</th><th>品名</th><th>分类</th><th>标价</th><th>现行价</th><th>状态</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="s in skus" :key="s.sku_code" :class="{ disabled: !s.enabled }">
          <td>{{ s.sku_code }}</td>
          <td>{{ s.title }}</td>
          <td>{{ s.category }}</td>
          <td>{{ s.list_price }}</td>
          <td>{{ s.current_price }}</td>
          <td>
            <span class="tag" :class="s.enabled ? 'ok' : 'bad'">{{ s.enabled ? '启用' : '停用' }}</span>
          </td>
          <td>
            <button class="btn ghost" type="button" :disabled="busy === s.sku_code" @click="toggle(s)">
              {{ s.enabled ? '停用' : '启用' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
