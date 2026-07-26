'use client';

import { Settings, Shield, KeyRound, Bell, Palette, User } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-[900px]">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Settings</h1>
        <p className="text-sm text-text-muted mt-0.5">Platform configuration</p>
      </div>

      {/* Settings sections */}
      <div className="space-y-4">
        <SettingsSection icon={Shield} title="Security" description="Configure export authorization, API access tokens, and raw value permissions.">
          <SettingsRow label="Export Auth Tokens" value="Configured" />
          <SettingsRow label="Authorized Targets" value="None set" />
          <SettingsRow label="Raw Value Policy" value="Masked by default" />
        </SettingsSection>

        <SettingsSection icon={KeyRound} title="API Keys" description="Connected provider API keys for verification and scanning.">
          <SettingsRow label="GitHub Token" value="Connected ✓" />
          <SettingsRow label="Censys PAT" value="Connected ✓" />
          <SettingsRow label="Mistral API Key" value="Connected ✓" />
          <SettingsRow label="Discord Webhook" value="Not set" />
        </SettingsSection>

        <SettingsSection icon={Bell} title="Notifications" description="Real-time alerting configuration for verified and active secrets.">
          <SettingsRow label="Discord Notifications" value="Disabled" />
          <SettingsRow label="Alert Threshold" value="High confidence (70+)" />
        </SettingsSection>

        <SettingsSection icon={Palette} title="Display" description="Theme, density, and preference settings.">
          <SettingsRow label="Theme" value="Dark" />
          <SettingsRow label="Default Sort" value="Newest first" />
        </SettingsSection>

        <SettingsSection icon={User} title="Profile" description="Account information and session settings.">
          <SettingsRow label="Session" value="Active" />
        </SettingsSection>
      </div>
    </div>
  );
}

function SettingsSection({ icon: Icon, title, description, children }: {
  icon: React.ElementType;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-4 h-4 text-text-muted" />
        <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
      </div>
      <p className="text-2xs text-text-muted mb-4">{description}</p>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function SettingsRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="text-sm text-text-muted">{value}</span>
    </div>
  );
}
