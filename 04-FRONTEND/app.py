import streamlit as st

st.set_page_config(page_title='IFRS Bridge', layout='wide')

st.title('IFRS Bridge Simulator')
st.write('Automated NAS→IFRS gap detection for Uzbek accountants')

with st.sidebar:
    st.write('### Navigation')
    st.write('- Upload your NAS statement')
    st.write('- Detect gaps')

st.info('📁 Project scaffold initialized. Phase 2 coding begins here.')
