<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const clock = ref('')
const batches = ref([])
const msg = ref('')
const err = ref('')
const result = ref(null)

async function refresh() {
  const c = await api.clock()
  clock.value = c.business_clock || ''
  batches.value = await api.batches()
}

async function saveClock() {
  msg.value = ''
  err.value = ''
  try {
    await api.setClock(clock.value)
    msg.value = '业务钟已更新'
    await refresh()
  } catch (e) {
    err.value = e.message
  }
}

async function applyDue() {
  msg.value = ''
  err.value = ''
  result.value = null
  try {
    result.value = await api.applyDue()
    if (result.value.applied) {
      msg.value = `已应用 ${result.value.ticket_count} 张改价单`
    } else if (result.value.rejected_ticket_count) {
      msg.value = `无改价单写入；整单拒绝 ${result.value.rejected_ticket_count} 张（含停用商品）`
    } else {
      msg.value = result.value.message || '没有可应用的改动'
    }
    await refresh()
  } catch (e) {
    err.value = e.message
  }
}

onMounted(() => refresh().catch((e) => (err.value = e.message)))
</script>

<template>
  <section class="hero">
    <h1>生效应用</h1>
    <p>拨动业务钟后，点「应用到期」将 effective_at ≤ 业务钟的改价单写入现行价签。</p>
  </section>

  <div class="panel">
    <h2>业务钟</h2>
    <div class="row">
      <div class="field" style="flex:1">
        <label>业务钟 (UTC)</label>
        <input v-model="clock" />
      </div>
      <button class="btn ghost" type="button" @click="saveClock">保存业务钟</button>
      <button class="btn warn" type="button" @click="applyDue">应用到期</button>
    </div>
    <p v-if="msg" class="msg ok">{{ msg }}</p>
    <p v-if="err" class="msg err">{{ err }}</p>

    <div v-if="result && result.rejected_tickets && result.rejected_tickets.length" class="notice bad">
      <strong>整单拒绝（停用商品策略：建单即拒）</strong>
      <ul>
        <li v-for="r in result.rejected_tickets" :key="r.ticket_no">
          {{ r.ticket_no }} — {{ r.reason }}；该单未写入任何价签
        </li>
      </ul>
    </div>
    <div v-if="result && result.skipped_lines && result.skipped_lines.length" class="notice warn">
      <strong>跳过停用行（策略：应用跳过）</strong>
      <ul>
        <li v-for="(r, i) in result.skipped_lines" :key="i">{{ r.ticket_no }} · {{ r.sku_code }} 未写入价签</li>
      </ul>
    </div>
    <pre v-if="result" style="margin-top:12px;font-size:0.82rem;color:var(--muted);white-space:pre-wrap">{{ JSON.stringify(result, null, 2) }}</pre>
  </div>

  <div class="panel">
    <h2>应用批次</h2>
    <table>
      <thead>
        <tr><th>批次</th><th>业务钟</th><th>已应用单</th><th>写入行</th><th>拒绝单</th><th>跳过行</th><th>状态</th><th>时间</th></tr>
      </thead>
      <tbody>
        <tr v-for="b in batches" :key="b.id">
          <td>{{ b.batch_no }}</td>
          <td>{{ b.clock_at }}</td>
          <td>{{ b.ticket_count }}</td>
          <td>{{ b.line_count }}</td>
          <td>{{ b.rejected_ticket_count }}</td>
          <td>{{ b.skipped_line_count }}</td>
          <td><span class="tag ok">{{ b.status }}</span></td>
          <td>{{ b.created_at }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
