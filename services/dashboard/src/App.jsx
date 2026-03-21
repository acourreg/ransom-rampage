import { useState } from 'react'
import InfraGraph from './components/InfraGraph.jsx'

const MOCK_NODES = [
  { id:'n1', name:'API Gateway',           type:'entry',      business_name:'User Entry Point',    business_category:'Operations',           revenue_exposure:69,    flows_supported:['PeerSwap','CoinSafe','QuickCash','AdCoin'], throughput:8,     defense:5,     visibility:7,     cost:3,     compliance_score:6,     compromised:false, locked:false, offline:false, fogged:false, isolated:false, has_mfa:false },
  { id:'n2', name:'Admin Panel',           type:'human',      business_name:'Control Center',      business_category:'People & Access',       revenue_exposure:21,    flows_supported:['PeerSwap','AdCoin'],                       throughput:3,     defense:2,     visibility:5,     cost:2,     compliance_score:4,     compromised:false, locked:false, offline:false, fogged:false, isolated:false, has_mfa:false },
  { id:'n3', name:'Payment Provider',      type:'vendor',     business_name:'Payment Hub',         business_category:'Unknown',              revenue_exposure:'???', flows_supported:[],                                          throughput:'???', defense:'???', visibility:'???', cost:'???', compliance_score:'???', compromised:false, locked:false, offline:false, fogged:true,  isolated:false, has_mfa:false },
  { id:'n4', name:'Core Database',         type:'database',   business_name:'Data Heart',          business_category:'Revenue Critical',     revenue_exposure:30,    flows_supported:['QuickCash'],                               throughput:9,     defense:8,     visibility:5,     cost:7,     compliance_score:7,     compromised:false, locked:false, offline:false, fogged:false, isolated:false, has_mfa:false },
  { id:'n5', name:'Transaction Server',    type:'server',     business_name:'Transaction Engine',  business_category:'Revenue Critical',     revenue_exposure:63,    flows_supported:['PeerSwap','CoinSafe','QuickCash'],          throughput:6,     defense:7,     visibility:6,     cost:5,     compliance_score:6,     compromised:false, locked:false, offline:false, fogged:false, isolated:false, has_mfa:false },
  { id:'n6', name:'Analytics Middleware',  type:'middleware', business_name:'Insight Processor',   business_category:'Revenue Critical',     revenue_exposure:18,    flows_supported:['CoinSafe'],                                throughput:7,     defense:6,     visibility:5,     cost:4,     compliance_score:5,     compromised:false, locked:false, offline:false, fogged:false, isolated:false, has_mfa:false },
  { id:'n7', name:'Security Middleware',   type:'middleware', business_name:'Protection Layer',    business_category:'Unknown',              revenue_exposure:'???', flows_supported:[],                                          throughput:'???', defense:'???', visibility:'???', cost:'???', compliance_score:'???', compromised:false, locked:false, offline:false, fogged:true,  isolated:false, has_mfa:false },
]
const MOCK_EDGES = [
  {from:'n1',to:'n4'},{from:'n1',to:'n5'},{from:'n2',to:'n6'},
  {from:'n3',to:'n5'},{from:'n4',to:'n5'},{from:'n4',to:'n6'},
  {from:'n4',to:'n7'},{from:'n6',to:'n7'},{from:'n7',to:'n5'}
]

export default function App() {
  const [selected, setSelected] = useState(null)
  return (
    <div style={{ padding: '2rem', background: '#F8FAFC', minHeight: '100vh' }}>
      <h2 style={{ fontFamily: 'Inter', fontWeight: 600, marginBottom: '1rem', color: '#0F172A' }}>
        InfraGraph — FE-2 Test
      </h2>
      <InfraGraph nodes={MOCK_NODES} edges={MOCK_EDGES} selectingTarget={false} onNodeSelect={setSelected} />
      {selected && (
        <p style={{ marginTop: '1rem', fontFamily: 'JetBrains Mono', fontSize: '0.8rem', color: '#64748B' }}>
          onNodeSelect fired: {selected.name}
        </p>
      )}
    </div>
  )
}
