import UploadCard from "@/components/UploadCard";

export default function UploadPage() {
  return (
    <div className="min-h-screen bg-slate-100 py-10 flex flex-col items-center">
      <div className="w-full max-w-3xl px-4">
        <h1 className="text-3xl font-bold text-gray-800 mb-6 text-center">Upload ESG Report</h1>
        <UploadCard />
      </div>
    </div>
  );
}
