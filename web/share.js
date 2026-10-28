// Runs on the server-rendered share page /c/{check_id}: counts the visit, and credits the sharer when the link
// carried ?ref=, even if this visitor never clicks through to the app.
import { ref, track } from './components/session.js';

const checkId = location.pathname.split('/')[2] || null;
track('visit', { checkId, props: { path: '/c' } });
if (ref) track('ref_visit', { checkId });
