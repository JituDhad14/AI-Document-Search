// src/pages/Profile.tsx
import React from "react";
import { useAuth } from "../auth/AuthProvider";

export const Profile: React.FC = () => {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-md text-center text-slate-400">
          <p>
            You are not logged in. Please{" "}
            <span className="text-emerald-300 font-medium">Login</span> to view your profile.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-8">
      {/* MAIN PROFILE CARD */}
      <div className="max-w-2xl mx-auto bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h2 className="text-2xl font-bold text-emerald-300 mb-3">Your Profile</h2>
        <div className="text-slate-200 space-y-3">
          <div>
            <span className="text-slate-400">Name:</span>{" "}
            <span className="font-medium">{user.name || "-"}</span>
          </div>
          <div>
            <span className="text-slate-400">Username:</span>{" "}
            <span className="font-medium">{user.username}</span>
          </div>
          <div>
            <span className="text-slate-400">Email:</span>{" "}
            <span className="font-medium">{user.email}</span>
          </div>
          <div>
            <span className="text-slate-400">Profession:</span>{" "}
            <span className="font-medium">{user.profession || "-"}</span>
          </div>
          <div>
            <span className="text-slate-400">Purpose:</span>{" "}
            <span className="font-medium">{user.purpose || "-"}</span>
          </div>
          <div>
            <span className="text-slate-400">Registered on:</span>{" "}
            <span className="font-medium">
              {new Date(user.createdAt).toLocaleString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
