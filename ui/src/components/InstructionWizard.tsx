import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useNavigate, useParams } from "@tanstack/react-router";
import { Outlet } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

export interface InstructionPhase {
  id: number;
  title: string;
}

interface InstructionsWizardProps {
  phases: InstructionPhase[];
  basePath: string;
  showPhaseNumbers?: boolean;
  onCompleteRedirect?: string;
}

export const InstructionsWizard: React.FC<InstructionsWizardProps> = ({
  phases,
  basePath,
  showPhaseNumbers = true,
  onCompleteRedirect = "/",
}) => {
  const { t } = useTranslation("tak");
  const navigate = useNavigate();
  //@ts-ignore
  const params = useParams({ from: `${basePath}/$phaseId` });
  //@ts-ignore
  const phaseIdParam = params.phaseId;
  const phaseId = phaseIdParam ? parseInt(phaseIdParam, 10) : phases[0].id;

  const currentPhaseIndex = phases.findIndex((p) => p.id === phaseId);
  const currentPhase = phases[currentPhaseIndex] || phases[0];
  const progressPercentage =
    ((currentPhaseIndex + 1) / phases.length) * 100;

  const handleNext = () => {
    if (currentPhaseIndex < phases.length - 1) {
      navigate({ to: `${basePath}/${phases[currentPhaseIndex + 1].id}` });
    } else {
      navigate({ to: onCompleteRedirect });
    }
  };

  const handlePrevious = () => {
    if (currentPhaseIndex > 0) {
      navigate({ to: `${basePath}/${phases[currentPhaseIndex - 1].id}` });
    }
  };

  const handlePhaseClick = (index: number) => {
    navigate({ to: `${basePath}/${phases[index].id}` });
  };

  return (
    <div className="min-h-screen flex flex-col gap-6 p-6">
      {/* Top bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            {showPhaseNumbers && (
              <span className="text-sm text-muted-foreground">
                {t("wizard.step_counter", {
                  current: currentPhaseIndex + 1,
                  total: phases.length
                })}
              </span>
            )}
          </h2>
        </div>
        <Progress value={progressPercentage} />
      </div>
      <h1 className="text-2xl font-bold">{currentPhase.title}</h1>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <Outlet />
      </div>

      {/* Navigation */}
      <div className="bg-background border-t p-6 flex items-center justify-between gap-4">
        <Button
          variant="outline"
          onClick={handlePrevious}
          disabled={currentPhaseIndex <= 0}
          className="gap-2"
        >
          <ChevronLeft className="w-4 h-4" />
          {t("wizard.previous")}
        </Button>

        <div className="flex gap-2">
          {phases.map((_, index) => (
            <button
              key={index}
              onClick={() => handlePhaseClick(index)}
              className={`h-2 rounded-full transition-all ${
                index === currentPhaseIndex
                  ? "bg-primary w-8"
                  : "bg-secondary w-2 hover:bg-secondary/70"
              }`}
              aria-label={`Go to phase ${index + 1}`}
            />
          ))}
        </div>

        <Button onClick={handleNext} className="gap-2">
          {currentPhaseIndex === phases.length - 1
            ? t("wizard.complete")
            : t("wizard.next")}
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
};
