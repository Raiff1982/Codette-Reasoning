import React, { useEffect, useState } from 'react';
import { FileText, Download, Loader, Trash2, AlertCircle } from 'lucide-react';
import { supabase, getSupabaseHeaders } from '@/lib/supabase';
import { useAuth } from '@/core/providers/AuthProvider';

interface FileListProps {
  darkMode: boolean;
  isAdmin?: boolean;
}

interface FileData {
  id: string;
  filename: string;
  storage_path: string;
  file_type: string;
  uploaded_at: string;
}

const FileList: React.FC<FileListProps> = ({ darkMode, isAdmin = false }) => {
  const { isAuthenticated } = useAuth();
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchFiles = async () => {
    try {
      setError(null);
      setLoading(true);

      const headers = await getSupabaseHeaders();
      if (!headers.Authorization) {
        throw new Error('Not authenticated. Please wait while signing in...');
      }

      const { data, error: fetchError } = await supabase
        .from('codette_files')
        .select('*')
        .order('uploaded_at', { ascending: false });

      if (fetchError) {
        throw fetchError;
      }

      setFiles(data || []);
    } catch (err: any) {
      console.error('Error fetching files:', err);
      setError(err.message || 'Failed to fetch files');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchFiles();
    }
  }, [isAuthenticated]);

  const handleDownload = async (file: FileData) => {
    try {
      setDownloading(file.id);
      setError(null);

      const { data, error: downloadError } = await supabase.storage
        .from('codette-files')
        .download(file.storage_path);

      if (downloadError) {
        throw downloadError;
      }

      const url = window.URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      console.error('Error downloading file:', err);
      setError(err.message || 'Failed to download file');
    } finally {
      setDownloading(null);
    }
  };

  const handleDelete = async (file: FileData) => {
    if (!isAdmin) return;
    
    if (!confirm('Are you sure you want to delete this file?')) return;

    try {
      setDeleting(file.id);
      setError(null);

      const { error: storageError } = await supabase.storage
        .from('codette-files')
        .remove([file.storage_path]);

      if (storageError) {
        throw storageError;
      }

      const { error: dbError } = await supabase
        .from('codette_files')
        .delete()
        .match({ id: file.id });

      if (dbError) {
        throw dbError;
      }

      setFiles(files.filter(f => f.id !== file.id));
    } catch (err: any) {
      console.error('Error deleting file:', err);
      setError(err.message || 'Failed to delete file');
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader className="animate-spin\" size={24} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`p-4 rounded-lg ${darkMode ? 'bg-red-900/20' : 'bg-red-50'}`}>
        <div className="flex items-start space-x-2">
          <AlertCircle className={`flex-shrink-0 ${darkMode ? 'text-red-400' : 'text-red-500'}`} size={20} />
          <div className="flex-1">
            <p className={`text-sm font-medium ${darkMode ? 'text-red-400' : 'text-red-800'}`}>
              Error
            </p>
            <p className={`text-sm mt-1 ${darkMode ? 'text-red-300' : 'text-red-600'}`}>
              {error}
            </p>
            <button
              onClick={fetchFiles}
              className={`mt-3 px-3 py-1 rounded-md text-sm ${
                darkMode
                  ? 'bg-red-900/30 hover:bg-red-900/50 text-red-300'
                  : 'bg-red-100 hover:bg-red-200 text-red-700'
              }`}
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold mb-3">Uploaded Files</h3>
      {files.length === 0 ? (
        <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          No files uploaded yet.
        </p>
      ) : (
        <div className="space-y-2">
          {files.map((file) => (
            <div
              key={file.id}
              className={`p-3 rounded-md ${
                darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-100 hover:bg-gray-200'
              } transition-colors flex items-center justify-between`}
            >
              <div className="flex items-center space-x-2">
                <FileText size={16} className="text-blue-500" />
                <div>
                  <p className="text-sm font-medium truncate max-w-[150px]">
                    {file.filename}
                  </p>
                  <p className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    {new Date(file.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleDownload(file)}
                  disabled={downloading === file.id}
                  className={`p-1 rounded-md transition-colors ${
                    darkMode
                      ? 'hover:bg-gray-500 text-gray-300'
                      : 'hover:bg-gray-300 text-gray-700'
                  }`}
                >
                  {downloading === file.id ? (
                    <Loader className="animate-spin\" size={16} />
                  ) : (
                    <Download size={16} />
                  )}
                </button>
                {isAdmin && (
                  <button
                    onClick={() => handleDelete(file)}
                    disabled={deleting === file.id}
                    className={`p-1 rounded-md transition-colors ${
                      darkMode
                        ? 'hover:bg-red-500 text-gray-300'
                        : 'hover:bg-red-100 text-red-600'
                    }`}
                  >
                    {deleting === file.id ? (
                      <Loader className="animate-spin\" size={16} />
                    ) : (
                      <Trash2 size={16} />
                    )}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileList;