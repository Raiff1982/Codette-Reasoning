import { format, formatDistanceToNow } from 'date-fns';

export const formatTimestamp = (timestamp: number | Date): string => {
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
  return format(date, 'PPpp');
};

export const getTimeSince = (timestamp: number | Date): string => {
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
  return formatDistanceToNow(date, { addSuffix: true });
};