import React, { useState, useEffect, useRef } from 'react';
import { Bell, CheckCheck, ExternalLink, X } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { notificationsApi } from '../api/notifications';
import { useNavigate } from 'react-router-dom';

export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const ref = useRef(null);
  const navigate = useNavigate();

  const fetchNotifications = async () => {
    try {
      const { data } = await notificationsApi.list({ limit: 10 });
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch (err) {
      console.error('Failed to load notifications', err);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleMarkAllRead = async () => {
    await notificationsApi.markAllRead();
    await fetchNotifications();
  };

  const handleClickNotification = async (notif) => {
    if (!notif.is_read) {
      await notificationsApi.markRead(notif.id);
      await fetchNotifications();
    }
    if (notif.link) {
      navigate(notif.link);
      setOpen(false);
    }
  };

  const getTypeColor = (type) => {
    const map = {
      document_indexed: 'bg-green-100 text-green-700',
      job_failed: 'bg-red-100 text-red-700',
      report_ready: 'bg-blue-100 text-blue-700',
      duplicate_detected: 'bg-yellow-100 text-yellow-700',
    };
    return map[type] || 'bg-slate-100 text-slate-600';
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => { setOpen(!open); if (!open) fetchNotifications(); }}
        className="relative p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
        title="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 bottom-full mb-2 w-80 bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden z-50">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50">
            <span className="font-semibold text-slate-900 text-sm">Notifications</span>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <CheckCheck size={14} /> Mark all read
                </button>
              )}
              <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X size={16} />
              </button>
            </div>
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-sm">
                <Bell size={24} className="mx-auto mb-2 text-slate-300" />
                No notifications
              </div>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => handleClickNotification(notif)}
                  className={`px-4 py-3 border-b border-slate-50 cursor-pointer hover:bg-slate-50 transition-colors ${
                    !notif.is_read ? 'bg-blue-50/50' : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${
                      !notif.is_read ? 'bg-blue-500' : 'bg-slate-200'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 leading-snug">{notif.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{notif.message}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {formatDistanceToNow(new Date(notif.created_at))} ago
                      </p>
                    </div>
                    {notif.link && <ExternalLink size={12} className="text-slate-300 mt-1 shrink-0" />}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
